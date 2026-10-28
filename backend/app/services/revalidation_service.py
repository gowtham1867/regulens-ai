from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.application import Application, ApplicationStatus, ApplicationStatusHistory
from app.models.document import Document, DocumentVersion, ExtractedField
from app.models.finding import ValidationRun, ValidationFinding, FindingStatus, TriggerType
from app.models.workflow import ClarificationRequest, ClarificationStatus, CorrectionSubmission
from app.services.rules_engine import ComplianceRulesEngine
from app.services.audit_service import record_audit_event
from app.services.notification_service import create_notification, notify_all_officers
from app.models.user import User


class RevalidationService:
    def __init__(self, db: Session):
        self.db = db

    def submit_correction(
        self,
        clarification_request_id: int,
        submitting_user: User,
        explanation: str,
        document_id: int,
        file_path: str,
        original_filename: str,
        file_hash: str,
        mime_type: str,
        file_size_bytes: int
    ) -> CorrectionSubmission:
        clarification = self.db.query(ClarificationRequest).filter(
            ClarificationRequest.id == clarification_request_id
        ).first()
        if not clarification:
            raise ValueError(f"ClarificationRequest {clarification_request_id} not found")

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # Determine next version number
        last_version = self.db.query(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(DocumentVersion.version_number.desc()).first()
        next_version_num = (last_version.version_number + 1) if last_version else 1

        # Create correction submission record
        correction = CorrectionSubmission(
            clarification_request_id=clarification_request_id,
            application_id=clarification.application_id,
            submitting_user_id=submitting_user.id,
            explanation=explanation,
            created_at=datetime.utcnow()
        )
        self.db.add(correction)
        self.db.flush()

        # Create new DocumentVersion (preserving historical versions!)
        new_version = DocumentVersion(
            document_id=document_id,
            version_number=next_version_num,
            file_path=file_path,
            original_filename=original_filename,
            file_hash=file_hash,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            status="PROCESSING",
            correction_submission_id=correction.id,
            uploaded_by_user_id=submitting_user.id,
            created_at=datetime.utcnow()
        )
        self.db.add(new_version)
        self.db.flush()

        # Run OCR and structured field extraction on newly submitted correction version
        try:
            from app.services.ocr_engine import OCREngine
            with open(file_path, "rb") as f_in:
                contents = f_in.read()
            auth_check = OCREngine.inspect_file_authenticity(contents, original_filename)
            ocr_result = OCREngine.extract_from_file(file_path, original_filename)

            new_version.page_count = ocr_result.get("page_count", 1)
            new_version.raw_extracted_text = ocr_result.get("raw_text", "")
            new_version.ocr_confidence = ocr_result.get("confidence", 0.85)

            raw_txt = ocr_result.get("raw_text", "").strip()
            is_scanned = ocr_result.get("is_scanned_image", False)
            doc_type_val = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)

            class_check = OCREngine.classify_document_content(
                raw_text=raw_txt,
                declared_type=doc_type_val,
                filename=original_filename,
                is_scanned_image=is_scanned
            )

            extracted = OCREngine.extract_structured_fields(
                document_type=doc_type_val,
                raw_text=raw_txt,
                pages=ocr_result.get("pages", [])
            )

            for ef in extracted:
                field_rec = ExtractedField(
                    document_version_id=new_version.id,
                    field_key=ef["field_key"],
                    field_label=ef["field_label"],
                    extracted_value=ef["extracted_value"],
                    normalized_value=ef.get("normalized_value"),
                    source_page=ef.get("source_page", 1),
                    confidence=ef.get("confidence", 0.90),
                    extraction_method=ef.get("extraction_method", "REGEX_PATTERN")
                )
                self.db.add(field_rec)

            if not class_check["is_plausible"]:
                new_version.status = "COMPLETED_WITH_WARNINGS"
                new_version.error_message = class_check["mismatch_reason"]
            elif len(extracted) == 0:
                new_version.status = "COMPLETED_WITH_WARNINGS"
                new_version.error_message = "No supported regulatory fields detected in replacement document."
            else:
                new_version.status = "COMPLETED"
                new_version.error_message = None

        except Exception as e:
            new_version.status = "FAILED"
            new_version.error_message = f"Correction processing failure: {str(e)}"

        # Run duplicate detection and requirements evaluation
        try:
            from app.services.anomaly_detector import AnomalyDetector
            from app.services.document_requirements_service import DocumentRequirementsEngine
            anom = AnomalyDetector(self.db)
            anom.scan_application_anomalies(clarification.application_id)

            req_eng = DocumentRequirementsEngine(self.db)
            req_eval = req_eng.evaluate_application_requirements(clarification.application_id)
            if req_eval.get("open_deficiencies_count", 0) == 0:
                clarification.status = ClarificationStatus.RESOLVED
            else:
                clarification.status = ClarificationStatus.RESPONDED
        except Exception:
            clarification.status = ClarificationStatus.RESPONDED
        
        # Update application status to CORRECTION_SUBMITTED
        app = clarification.application
        old_status = app.status.value
        app.status = ApplicationStatus.CORRECTION_SUBMITTED

        # Record Status History
        status_history = ApplicationStatusHistory(
            application_id=app.id,
            from_status=old_status,
            to_status=app.status.value,
            changed_by_user_id=submitting_user.id,
            reason=f"Correction evidence uploaded for Clarification #{clarification.id}: {explanation[:150]}",
            created_at=datetime.utcnow()
        )
        self.db.add(status_history)
        self.db.commit()

        # Audit event
        record_audit_event(
            db=self.db,
            action="SUBMIT_CORRECTION_DOCUMENT",
            entity_type="APPLICATION",
            entity_id=str(app.id),
            actor=submitting_user,
            before_state={"status": old_status},
            after_state={"status": app.status.value, "new_version_number": next_version_num},
            details=f"Corrected document version {next_version_num} uploaded for '{doc.title}' in response to Clarification #{clarification.id}."
        )

        # Notify officers
        notify_all_officers(
            db=self.db,
            title="Correction Document Submitted",
            message=f"Institution submitted corrected evidence (v{next_version_num}) for Application {app.reference_no}: {doc.title}.",
            notification_type="INFO",
            link=f"/applications/{app.id}",
            application_id=app.id,
            institution_id=app.institution_id,
            action_type="CORRECTION_SUBMITTED",
            details=explanation
        )

        return correction

    def execute_change_aware_revalidation(
        self,
        application_id: int,
        triggering_user: Optional[User] = None,
        reason: Optional[str] = None
    ) -> ValidationRun:
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # Set status to REVALIDATION
        old_status = app.status.value
        app.status = ApplicationStatus.REVALIDATION
        self.db.commit()

        # Re-run requirements checklist evaluation and anomaly scanning
        from app.services.document_requirements_service import DocumentRequirementsEngine
        from app.services.anomaly_detector import AnomalyDetector
        req_eng = DocumentRequirementsEngine(self.db)
        req_eval = req_eng.evaluate_application_requirements(application_id)
        anom = AnomalyDetector(self.db)
        anom.scan_application_anomalies(application_id)

        engine = ComplianceRulesEngine(self.db)
        val_run = engine.execute_validation_run(
            application_id=application_id,
            trigger_type=TriggerType.CHANGE_AWARE_REVALIDATION,
            triggering_change=reason or "Selective revalidation on corrected evidence"
        )

        # Compare findings: Check if prior critical/major findings are resolved
        active_failures = self.db.query(ValidationFinding).filter(
            ValidationFinding.application_id == application_id,
            ValidationFinding.is_active == True,
            ValidationFinding.status == FindingStatus.FAILED
        ).count()

        if active_failures == 0:
            app.status = ApplicationStatus.READY_FOR_DECISION
        else:
            app.status = ApplicationStatus.UNDER_REVIEW

        self.db.commit()

        record_audit_event(
            db=self.db,
            action="EXECUTE_REVALIDATION_RUN",
            entity_type="APPLICATION",
            entity_id=str(application_id),
            actor=triggering_user,
            before_state={"status": old_status},
            after_state={"status": app.status.value, "validation_run_id": val_run.id},
            details=f"Selective revalidation run #{val_run.run_number} finished. Passed: {val_run.passed_count}, Failed: {val_run.failed_count}."
        )

        return val_run

