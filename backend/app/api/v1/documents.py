import os
import uuid
import shutil
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.institution import InstitutionMembership
from app.models.application import Application
from app.models.document import (
    Document,
    DocumentVersion,
    ExtractedField,
    DocumentType,
    ProcessingStatus
)
from app.models.deficiency import ApplicationDeficiency, DeficiencyStatus
from app.models.duplicate import DuplicateRecord, DuplicateStatus
from app.schemas.all_schemas import (
    DocumentResponse,
    DocumentVersionResponse,
    ExtractedFieldResponse,
    FieldCorrectionRequest
)
from app.services.ocr_engine import OCREngine
from app.services.audit_service import record_audit_event
from app.services.document_requirements_service import DocumentRequirementsEngine
from app.services.anomaly_detector import AnomalyDetector
from app.services.rules_engine import ComplianceRulesEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Documents & OCR"])


@router.get("/applications/{application_id}/documents", response_model=List[DocumentResponse])
def list_application_documents(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership or membership.institution_id != app.institution_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

    docs = db.query(Document).filter(Document.application_id == application_id).all()
    results = []

    for d in docs:
        latest_v = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == d.id
        ).order_by(DocumentVersion.version_number.desc()).first()

        latest_resp = None
        if latest_v:
            fields = db.query(ExtractedField).filter(
                ExtractedField.document_version_id == latest_v.id
            ).all()

            v_status = latest_v.status.value if hasattr(latest_v.status, "value") else str(latest_v.status)

            latest_resp = {
                "id": latest_v.id,
                "version_number": latest_v.version_number,
                "original_filename": latest_v.original_filename,
                "file_hash": latest_v.file_hash,
                "mime_type": latest_v.mime_type,
                "file_size_bytes": latest_v.file_size_bytes,
                "page_count": latest_v.page_count,
                "status": v_status,
                "error_message": latest_v.error_message,
                "ocr_confidence": latest_v.ocr_confidence,
                "created_at": latest_v.created_at,
                "extracted_fields": [
                    {
                        "id": f.id,
                        "field_key": f.field_key,
                        "field_label": f.field_label,
                        "extracted_value": f.extracted_value,
                        "normalized_value": f.normalized_value,
                        "source_page": f.source_page,
                        "confidence": f.confidence,
                        "is_manually_corrected": f.is_manually_corrected,
                        "corrected_value": f.corrected_value,
                        "correction_reason": f.correction_reason
                    }
                    for f in fields
                ]
            }

        all_v_count = db.query(DocumentVersion).filter(DocumentVersion.document_id == d.id).count()
        doc_type_str = d.document_type.value if hasattr(d.document_type, "value") else str(d.document_type)

        results.append({
            "id": d.id,
            "application_id": d.application_id,
            "document_type": doc_type_str,
            "title": d.title,
            "is_required": d.is_required,
            "created_at": d.created_at,
            "latest_version": latest_resp,
            "all_versions_count": all_v_count
        })

    return results


@router.post("/applications/{application_id}/documents", response_model=DocumentResponse)
def upload_document(
    application_id: int,
    document_type: str = Form(...),
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership or membership.institution_id != app.institution_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

    filename = file.filename or "uploaded_document.pdf"
    safe_ext = os.path.splitext(filename)[1].lower()
    ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
    if safe_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{safe_ext}'. Supported formats: PDF, PNG, JPG, JPEG"
        )

    # Read and validate content
    contents = file.file.read()
    file_size = len(contents)
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file cannot be empty.")
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({round(file_size / (1024 * 1024), 2)}MB) exceeds maximum allowed limit (15MB)"
        )

    # Normalize DocumentType safely
    norm_doc_type = document_type.strip()
    try:
        doc_enum = DocumentType(norm_doc_type)
    except ValueError:
        upper_norm = norm_doc_type.upper().replace(" ", "_")
        try:
            doc_enum = DocumentType(upper_norm)
        except ValueError:
            ALIAS_MAP = {
                "LAND_TITLE": DocumentType.LAND_DOCUMENTS,
                "LAND_RECORD": DocumentType.LAND_DOCUMENTS,
                "LAND": DocumentType.LAND_DOCUMENTS,
                "LAND_USE": DocumentType.LAND_USE_CERTIFICATE,
                "AFFILIATION": DocumentType.AFFILIATION_ORDER,
                "FIRE": DocumentType.FIRE_SAFETY_CERTIFICATE,
                "AUDIT": DocumentType.AUDITED_FINANCIALS
            }
            doc_enum = ALIAS_MAP.get(upper_norm, DocumentType.OTHER)

    # Compute SHA-256 hash
    file_hash = OCREngine.calculate_file_hash(contents)

    # Secure random filename storage
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    storage_filename = f"{uuid.uuid4().hex}{safe_ext}"
    storage_path = os.path.join(settings.UPLOAD_DIR, storage_filename)

    with open(storage_path, "wb") as f_out:
        f_out.write(contents)

    # Find existing Document record or create new one
    equiv_types = [doc_enum]
    if doc_enum in (DocumentType.LAND_DOCUMENT, DocumentType.LAND_DOCUMENTS, DocumentType.LAND_USE_CERTIFICATE):
        equiv_types = [DocumentType.LAND_DOCUMENT, DocumentType.LAND_DOCUMENTS, DocumentType.LAND_USE_CERTIFICATE]
    elif doc_enum in (DocumentType.AFFILIATION_CERTIFICATE, DocumentType.AFFILIATION_ORDER):
        equiv_types = [DocumentType.AFFILIATION_CERTIFICATE, DocumentType.AFFILIATION_ORDER]
    elif doc_enum in (DocumentType.AUDIT_STATEMENT, DocumentType.AUDITED_FINANCIALS):
        equiv_types = [DocumentType.AUDIT_STATEMENT, DocumentType.AUDITED_FINANCIALS]

    doc = db.query(Document).filter(
        Document.application_id == application_id,
        Document.document_type.in_(equiv_types)
    ).first()

    clean_title = title.strip() if (title and title.strip()) else doc_enum.value.replace("_", " ").title()

    if not doc:
        doc = Document(
            application_id=application_id,
            document_type=doc_enum,
            title=clean_title,
            is_required=True
        )
        db.add(doc)
        db.flush()
    else:
        if title and title.strip():
            doc.title = clean_title

    # Determine version number
    last_v = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc.id
    ).order_by(DocumentVersion.version_number.desc()).first()
    v_num = (last_v.version_number + 1) if last_v else 1

    mime = file.content_type
    if not mime or mime == "application/octet-stream":
        mime = "application/pdf" if safe_ext == ".pdf" else f"image/{safe_ext.lstrip('.')}"

    doc_version = DocumentVersion(
        document_id=doc.id,
        version_number=v_num,
        file_path=storage_path,
        original_filename=filename,
        file_hash=file_hash,
        mime_type=mime,
        file_size_bytes=file_size,
        status=ProcessingStatus.PROCESSING,
        uploaded_by_user_id=current_user.id,
        created_at=datetime.utcnow()
    )
    db.add(doc_version)
    db.flush()

    # Execute File Authenticity, OCR, Document Classification, and Field Extraction
    try:
        auth_check = OCREngine.inspect_file_authenticity(contents, filename)
        if not auth_check["is_valid"]:
            doc_version.status = ProcessingStatus.FAILED
            doc_version.error_message = auth_check["error"] or "Unsupported or corrupted file binary."
        else:
            ocr_result = OCREngine.extract_from_file(storage_path, filename)
            doc_version.page_count = ocr_result.get("page_count", 1)
            doc_version.raw_extracted_text = ocr_result.get("raw_text", "")
            doc_version.ocr_confidence = ocr_result.get("confidence", 0.85)

            raw_txt = ocr_result.get("raw_text", "").strip()
            is_scanned = ocr_result.get("is_scanned_image", False)
            doc_type_val = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type)

            # Classify document against declared regulatory category
            class_check = OCREngine.classify_document_content(
                raw_text=raw_txt,
                declared_type=doc_type_val,
                filename=filename,
                is_scanned_image=is_scanned
            )

            # Extract structured fields according to category schema
            extracted = OCREngine.extract_structured_fields(
                document_type=doc_type_val,
                raw_text=raw_txt,
                pages=ocr_result.get("pages", [])
            )

            # Persist extracted fields
            for ef in extracted:
                field_rec = ExtractedField(
                    document_version_id=doc_version.id,
                    field_key=ef["field_key"],
                    field_label=ef["field_label"],
                    extracted_value=ef["extracted_value"],
                    normalized_value=ef.get("normalized_value"),
                    source_page=ef.get("source_page", 1),
                    confidence=ef.get("confidence", 0.90),
                    extraction_method=ef.get("extraction_method", "REGEX_PATTERN")
                )
                db.add(field_rec)

            # Set honest, accurate processing status and error message
            if not class_check["is_plausible"]:
                doc_version.status = ProcessingStatus.COMPLETED_WITH_WARNINGS
                doc_version.error_message = class_check["mismatch_reason"]
            elif auth_check.get("has_extension_mismatch"):
                doc_version.status = ProcessingStatus.COMPLETED_WITH_WARNINGS
                doc_version.error_message = auth_check["error"]
            elif len(extracted) == 0:
                doc_version.status = ProcessingStatus.COMPLETED_WITH_WARNINGS
                if is_scanned:
                    doc_version.error_message = "Uploaded file is a scanned image/photo without digital text layer. Visual manual verification required."
                else:
                    doc_version.error_message = "No supported regulatory fields detected in document text."
            else:
                doc_version.status = ProcessingStatus.COMPLETED
                doc_version.error_message = None

    except Exception as e:
        logger.warning(f"Text/OCR extraction exception on {storage_path}: {e}", exc_info=True)
        doc_version.status = ProcessingStatus.FAILED
        doc_version.error_message = f"Text extraction warning / unprocessable format: {str(e)}"

    db.commit()
    db.refresh(doc)

    record_audit_event(
        db=db,
        action="UPLOAD_DOCUMENT",
        entity_type="DOCUMENT",
        entity_id=str(doc.id),
        actor=current_user,
        details=f"Uploaded '{filename}' (v{v_num}) for application {app.reference_no}. Hash: {file_hash[:16]}..."
    )

    # Run full compliance pipeline: Requirements checklist, Anomaly & Duplicate scan, and Rules Engine
    try:
        req_engine = DocumentRequirementsEngine(db)
        req_engine.evaluate_application_requirements(application_id)

        anom_detector = AnomalyDetector(db)
        anom_detector.scan_application_anomalies(application_id)

        rules_eng = ComplianceRulesEngine(db)
        rules_eng.execute_validation_run(
            application_id=application_id,
            trigger_type="DOCUMENT_UPLOAD",
            triggering_change=f"Uploaded '{filename}' (v{v_num})"
        )
    except Exception as eval_err:
        logger.warning(f"Post-upload evaluation warning: {eval_err}", exc_info=True)

    # Return refreshed response
    all_docs = list_application_documents(application_id, current_user, db)
    matched = next((d for d in all_docs if d["id"] == doc.id), None)
    return matched or all_docs[-1]


@router.get("/document-versions/{version_id}/download")
@router.get("/document-versions/{version_id}/preview")
def download_document_version(
    version_id: int,
    inline: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Protected document retrieval. Ensures only authorized parties can access files.
    Supports inline preview or attachment download.
    """
    doc_v = db.query(DocumentVersion).filter(DocumentVersion.id == version_id).first()
    if not doc_v:
        raise HTTPException(status_code=404, detail="Document version not found")

    app = doc_v.document.application
    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership or membership.institution_id != app.institution_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

    if not os.path.exists(doc_v.file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Physical document file '{doc_v.original_filename}' is missing on server storage"
        )

    disposition = "inline" if inline else "attachment"
    return FileResponse(
        path=doc_v.file_path,
        filename=doc_v.original_filename,
        media_type=doc_v.mime_type,
        content_disposition_type=disposition
    )


@router.patch("/extracted-fields/{field_id}/correct", response_model=ExtractedFieldResponse)
def correct_extracted_field(
    field_id: int,
    correction: FieldCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Authorized manual correction of OCR-extracted field values.
    Preserves original extraction and logs correction audit trail.
    """
    field = db.query(ExtractedField).filter(ExtractedField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Extracted field not found")

    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Only authorized AICTE Officers can correct extracted fields")

    old_val = field.extracted_value
    field.is_manually_corrected = True
    field.corrected_value = correction.corrected_value.strip()
    field.corrected_by_user_id = current_user.id
    field.correction_reason = correction.reason
    field.corrected_at = datetime.utcnow()
    db.commit()
    db.refresh(field)

    record_audit_event(
        db=db,
        action="MANUAL_FIELD_CORRECTION",
        entity_type="EXTRACTED_FIELD",
        entity_id=str(field.id),
        actor=current_user,
        before_state={"value": old_val},
        after_state={"corrected_value": field.corrected_value, "reason": correction.reason},
        details=f"Field '{field.field_key}' corrected by {current_user.full_name}."
    )

    return {
        "id": field.id,
        "field_key": field.field_key,
        "field_label": field.field_label,
        "extracted_value": field.extracted_value,
        "normalized_value": field.normalized_value,
        "source_page": field.source_page,
        "confidence": field.confidence,
        "is_manually_corrected": field.is_manually_corrected,
        "corrected_value": field.corrected_value,
        "correction_reason": field.correction_reason
    }


@router.get("/applications/{application_id}/requirements")
def get_application_requirements(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluate category-specific document checklist against official AICTE Approval Process Handbook (APH).
    Identifies missing documents, missing required fields, and active deficiencies.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    req_engine = DocumentRequirementsEngine(db)
    return req_engine.evaluate_application_requirements(application_id)


@router.get("/applications/{application_id}/deficiencies")
def list_application_deficiencies(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all active and resolved deficiencies for an application.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    defs = db.query(ApplicationDeficiency).filter(
        ApplicationDeficiency.application_id == application_id
    ).order_by(ApplicationDeficiency.created_at.desc()).all()

    return [
        {
            "id": d.id,
            "rule_code": d.rule_code,
            "document_type": d.document_type,
            "deficiency_type": d.deficiency_type.value if hasattr(d.deficiency_type, "value") else str(d.deficiency_type),
            "severity": d.severity,
            "title": d.title,
            "description": d.description,
            "reason": d.reason,
            "required_action": d.required_action,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "affected_document_version_id": d.affected_document_version_id,
            "resolved_by_document_version_id": d.resolved_by_document_version_id,
            "resolution_notes": d.resolution_notes,
            "created_at": d.created_at,
            "resolved_at": d.resolved_at
        }
        for d in defs
    ]


@router.patch("/applications/{application_id}/deficiencies/{deficiency_id}")
def resolve_application_deficiency(
    application_id: int,
    deficiency_id: int,
    resolution_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Officer action to resolve or waive a deficiency with justification.
    """
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Only authorized AICTE Officers can resolve deficiencies manually")

    d = db.query(ApplicationDeficiency).filter(
        ApplicationDeficiency.id == deficiency_id,
        ApplicationDeficiency.application_id == application_id
    ).first()
    if not d:
        raise HTTPException(status_code=404, detail="Deficiency not found")

    new_status = resolution_data.get("status", "RESOLVED")
    try:
        d.status = DeficiencyStatus(new_status)
    except ValueError:
        d.status = DeficiencyStatus.RESOLVED

    d.resolution_notes = resolution_data.get("resolution_notes", f"Manually resolved by Officer {current_user.full_name}")
    d.resolved_at = datetime.utcnow()
    db.commit()

    record_audit_event(
        db=db,
        action="RESOLVE_DEFICIENCY",
        entity_type="DEFICIENCY",
        entity_id=str(d.id),
        actor=current_user,
        details=f"Deficiency '{d.title}' resolved by officer. Status: {d.status.value}. Notes: {d.resolution_notes}"
    )

    return {"message": "Deficiency resolved successfully", "id": d.id, "status": d.status.value}


@router.get("/applications/{application_id}/duplicates")
def list_application_duplicates(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List exact and potential duplicate candidate records detected across the database.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    dups = db.query(DuplicateRecord).filter(
        DuplicateRecord.application_id == application_id
    ).order_by(DuplicateRecord.created_at.desc()).all()

    results = []
    for d in dups:
        matched_v = d.matched_document_version
        matched_app = matched_v.document.application if (matched_v and matched_v.document) else None
        results.append({
            "id": d.id,
            "document_version_id": d.document_version_id,
            "matched_document_version_id": d.matched_document_version_id,
            "match_type": d.match_type.value if hasattr(d.match_type, "value") else str(d.match_type),
            "similarity_score": d.similarity_score,
            "matched_identifier": d.matched_identifier,
            "explanation": d.explanation,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "officer_resolution_notes": d.officer_resolution_notes,
            "resolved_at": d.resolved_at,
            "created_at": d.created_at,
            "matched_filename": matched_v.original_filename if matched_v else "N/A",
            "matched_app_ref": matched_app.reference_no if matched_app else "N/A",
            "matched_institution": matched_app.institution.name if matched_app else "N/A"
        })
    return results


@router.patch("/applications/{application_id}/duplicates/{duplicate_id}")
def resolve_application_duplicate(
    application_id: int,
    duplicate_id: int,
    resolution_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Officer action to review duplicate candidate and determine legitimate reuse vs duplicate flag.
    """
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Only authorized AICTE Officers can resolve duplicate detections")

    dup = db.query(DuplicateRecord).filter(
        DuplicateRecord.id == duplicate_id,
        DuplicateRecord.application_id == application_id
    ).first()
    if not dup:
        raise HTTPException(status_code=404, detail="Duplicate record not found")

    new_status = resolution_data.get("status", "LEGITIMATE_REUSE")
    try:
        dup.status = DuplicateStatus(new_status)
    except ValueError:
        dup.status = DuplicateStatus.LEGITIMATE_REUSE

    dup.officer_resolution_notes = resolution_data.get("officer_resolution_notes", f"Reviewed by Officer {current_user.full_name}")
    dup.resolved_by_user_id = current_user.id
    dup.resolved_at = datetime.utcnow()
    db.commit()

    record_audit_event(
        db=db,
        action="RESOLVE_DUPLICATE_FLAG",
        entity_type="DUPLICATE_RECORD",
        entity_id=str(dup.id),
        actor=current_user,
        details=f"Duplicate flag resolved as {dup.status.value} by {current_user.full_name}. Notes: {dup.officer_resolution_notes}"
    )

    return {"message": "Duplicate record resolved", "id": dup.id, "status": dup.status.value}

