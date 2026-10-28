import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.application import Application
from app.models.document import Document, DocumentVersion, ExtractedField
from app.models.duplicate import DuplicateRecord, DuplicateMatchType, DuplicateStatus


class AnomalyDetector:
    def __init__(self, db: Session):
        self.db = db

    def scan_application(self, application_id: int) -> List[Dict[str, Any]]:
        return self.scan_application_anomalies(application_id)

    def scan_application_anomalies(self, application_id: int) -> List[Dict[str, Any]]:
        anomalies: List[Dict[str, Any]] = []
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            return anomalies

        doc_versions = self.db.query(DocumentVersion).join(Document).filter(
            Document.application_id == application_id
        ).all()

        today = datetime.utcnow().date()

        # =========================================================================
        # 1. EXACT DUPLICATE FILE HASH DETECTION (Cryptographic SHA-256)
        # =========================================================================
        for dv in doc_versions:
            collisions = self.db.query(DocumentVersion).join(Document).join(Application).filter(
                DocumentVersion.file_hash == dv.file_hash,
                DocumentVersion.id != dv.id
            ).all()

            for c in collisions:
                c_app = c.document.application
                is_same_institution = (c_app.institution_id == app.institution_id)
                is_cross_application = (c_app.id != application_id)

                # Persist DuplicateRecord if not already tracked
                existing_dup = self.db.query(DuplicateRecord).filter(
                    DuplicateRecord.application_id == application_id,
                    DuplicateRecord.document_version_id == dv.id,
                    DuplicateRecord.matched_document_version_id == c.id,
                    DuplicateRecord.match_type == DuplicateMatchType.EXACT_HASH
                ).first()

                match_exp = (
                    f"Cryptographic SHA-256 fingerprint ({dv.file_hash[:16]}...) is identical to file '{c.original_filename}' (v{c.version_number}) "
                    f"submitted in Application {c_app.reference_no} ({c_app.institution.name})."
                )

                if not existing_dup:
                    new_dup = DuplicateRecord(
                        application_id=application_id,
                        document_version_id=dv.id,
                        matched_document_version_id=c.id,
                        match_type=DuplicateMatchType.EXACT_HASH,
                        similarity_score=1.0,
                        matched_identifier=dv.file_hash,
                        explanation=match_exp,
                        status=DuplicateStatus.DETECTED,
                        created_at=datetime.utcnow()
                    )
                    self.db.add(new_dup)

                severity = "CRITICAL" if not is_same_institution else "MAJOR"
                action = (
                    "Investigate unauthorized file-sharing or credential submission across unrelated technical institutions."
                    if not is_same_institution
                    else "Verify if multi-cycle document reuse is legally permitted under current APH regulations."
                )

                anomalies.append({
                    "anomaly_type": "DUPLICATE_FILE_FINGERPRINT",
                    "severity": severity,
                    "document_version_id": dv.id,
                    "matched_version_id": c.id,
                    "filename": dv.original_filename,
                    "matched_filename": c.original_filename,
                    "matched_app_ref": c_app.reference_no,
                    "matched_institution": c_app.institution.name,
                    "is_same_institution": is_same_institution,
                    "file_hash": dv.file_hash,
                    "explanation": match_exp,
                    "recommended_action": action,
                    "confidence": 1.0
                })

        # =========================================================================
        # 2. POTENTIAL DUPLICATE BY CERTIFICATE / REFERENCE NUMBER
        # =========================================================================
        extracted_cert_fields = self.db.query(ExtractedField).join(DocumentVersion).join(Document).filter(
            Document.application_id == application_id,
            ExtractedField.field_key == "certificate_number"
        ).all()

        for ef in extracted_cert_fields:
            cert_val = (ef.normalized_value or ef.extracted_value or "").strip().upper()
            if cert_val and len(cert_val) > 4:
                matches = self.db.query(ExtractedField).join(DocumentVersion).join(Document).join(Application).filter(
                    ExtractedField.field_key == "certificate_number",
                    (ExtractedField.normalized_value == cert_val) | (ExtractedField.extracted_value == cert_val),
                    ExtractedField.document_version_id != ef.document_version_id
                ).all()

                for m in matches:
                    m_app = m.document_version.document.application
                    is_cross_inst = (m_app.institution_id != app.institution_id)

                    exp = (
                        f"Extracted Certificate / Reference Number '{cert_val}' matches a document submitted in "
                        f"Application {m_app.reference_no} by '{m_app.institution.name}'."
                    )

                    # Persist DuplicateRecord
                    existing_dup = self.db.query(DuplicateRecord).filter(
                        DuplicateRecord.application_id == application_id,
                        DuplicateRecord.document_version_id == ef.document_version_id,
                        DuplicateRecord.matched_document_version_id == m.document_version_id,
                        DuplicateRecord.match_type == DuplicateMatchType.CERTIFICATE_NUMBER
                    ).first()

                    if not existing_dup:
                        new_dup = DuplicateRecord(
                            application_id=application_id,
                            document_version_id=ef.document_version_id,
                            matched_document_version_id=m.document_version_id,
                            match_type=DuplicateMatchType.CERTIFICATE_NUMBER,
                            similarity_score=0.98,
                            matched_identifier=cert_val,
                            explanation=exp,
                            status=DuplicateStatus.DETECTED,
                            created_at=datetime.utcnow()
                        )
                        self.db.add(new_dup)

                    anomalies.append({
                        "anomaly_type": "CROSS_INSTITUTION_CERTIFICATE_COLLISION" if is_cross_inst else "POTENTIAL_DUPLICATE_CERTIFICATE",
                        "severity": "CRITICAL" if is_cross_inst else "MAJOR",
                        "document_version_id": ef.document_version_id,
                        "matched_version_id": m.document_version_id,
                        "certificate_number": cert_val,
                        "matched_app_ref": m_app.reference_no,
                        "matched_institution": m_app.institution.name,
                        "explanation": exp,
                        "recommended_action": "Initiate Issuing Authority verification to confirm legitimate recipient of certificate.",
                        "confidence": 0.95
                    })

        # =========================================================================
        # 3. TEXT SIMILARITY MATCH (Near-Duplicate Modified Documents)
        # =========================================================================
        for dv in doc_versions:
            if not dv.raw_extracted_text or len(dv.raw_extracted_text) < 100:
                continue

            dv_tokens = set(re.findall(r'\b[A-Za-z]{4,}\b', dv.raw_extracted_text.lower()))
            if len(dv_tokens) < 15:
                continue

            # Compare against other versions with different hashes
            other_vers = self.db.query(DocumentVersion).join(Document).join(Application).filter(
                DocumentVersion.id != dv.id,
                DocumentVersion.file_hash != dv.file_hash,
                DocumentVersion.raw_extracted_text.isnot(None)
            ).all()

            for ov in other_vers:
                if not ov.raw_extracted_text or len(ov.raw_extracted_text) < 100:
                    continue
                ov_tokens = set(re.findall(r'\b[A-Za-z]{4,}\b', ov.raw_extracted_text.lower()))
                if len(ov_tokens) < 15:
                    continue

                intersection = len(dv_tokens.intersection(ov_tokens))
                union = len(dv_tokens.union(ov_tokens))
                jaccard = intersection / max(1, union)

                if jaccard >= 0.85:
                    ov_app = ov.document.application
                    exp = (
                        f"Substantial textual similarity ({int(jaccard * 100)}% token overlap) identified between '{dv.original_filename}' "
                        f"and '{ov.original_filename}' (App {ov_app.reference_no}, {ov_app.institution.name})."
                    )

                    existing_dup = self.db.query(DuplicateRecord).filter(
                        DuplicateRecord.application_id == application_id,
                        DuplicateRecord.document_version_id == dv.id,
                        DuplicateRecord.matched_document_version_id == ov.id,
                        DuplicateRecord.match_type == DuplicateMatchType.TEXT_SIMILARITY
                    ).first()

                    if not existing_dup:
                        new_dup = DuplicateRecord(
                            application_id=application_id,
                            document_version_id=dv.id,
                            matched_document_version_id=ov.id,
                            match_type=DuplicateMatchType.TEXT_SIMILARITY,
                            similarity_score=round(jaccard, 2),
                            explanation=exp,
                            status=DuplicateStatus.DETECTED,
                            created_at=datetime.utcnow()
                        )
                        self.db.add(new_dup)

                    anomalies.append({
                        "anomaly_type": "HIGH_TEXT_SIMILARITY_DUPLICATE",
                        "severity": "MAJOR",
                        "document_version_id": dv.id,
                        "matched_version_id": ov.id,
                        "filename": dv.original_filename,
                        "matched_filename": ov.original_filename,
                        "similarity_score": round(jaccard, 2),
                        "explanation": exp,
                        "recommended_action": "Inspect physical documents to verify if this is a modified revision or cloned template.",
                        "confidence": round(jaccard, 2)
                    })

        # =========================================================================
        # 4. FIELD-LEVEL CONFLICTS & CONTRADICTORY DATES
        # =========================================================================
        for dv in doc_versions:
            fields = {f.field_key: f for f in dv.extracted_fields}
            
            # A. Issue Date >= Expiry Date
            issue_f = fields.get("issue_date")
            expiry_f = fields.get("expiry_date")
            if issue_f and expiry_f:
                try:
                    iss_dt = datetime.strptime(issue_f.normalized_value or issue_f.extracted_value, "%Y-%m-%d")
                    exp_dt = datetime.strptime(expiry_f.normalized_value or expiry_f.extracted_value, "%Y-%m-%d")
                    if iss_dt >= exp_dt:
                        anomalies.append({
                            "anomaly_type": "CONTRADICTORY_DATES",
                            "severity": "CRITICAL",
                            "document_version_id": dv.id,
                            "filename": dv.original_filename,
                            "explanation": f"Chronological impossibility: Issue date ({issue_f.extracted_value}) is on or after Expiry date ({expiry_f.extracted_value}).",
                            "recommended_action": "Inspect document for date manipulation or issuer typographical defect.",
                            "confidence": 0.98
                        })
                except Exception:
                    pass

            # B. Institution Name Mismatch
            inst_f = fields.get("institution_name")
            if inst_f and inst_f.extracted_value:
                ext_name = inst_f.extracted_value.lower()
                app_inst_name = app.institution.name.lower()
                # Check token overlap
                e_tokens = set(re.findall(r'\b[a-z]{3,}\b', ext_name))
                a_tokens = set(re.findall(r'\b[a-z]{3,}\b', app_inst_name))
                overlap = len(e_tokens.intersection(a_tokens))
                if len(e_tokens) > 2 and overlap == 0:
                    anomalies.append({
                        "anomaly_type": "INSTITUTION_NAME_MISMATCH",
                        "severity": "CRITICAL",
                        "document_version_id": dv.id,
                        "filename": dv.original_filename,
                        "explanation": f"Extracted institution name '{inst_f.extracted_value}' diverges completely from applicant institution '{app.institution.name}'.",
                        "recommended_action": "Verify if certificate was issued to a third-party organization or prior entity name.",
                        "confidence": 0.90
                    })

            # C. Document Type Mismatch Hint
            if dv.error_message and "mismatch" in dv.error_message.lower():
                anomalies.append({
                    "anomaly_type": "DOCUMENT_TYPE_MISMATCH",
                    "severity": "MAJOR",
                    "document_version_id": dv.id,
                    "filename": dv.original_filename,
                    "explanation": dv.error_message,
                    "recommended_action": "Request college to upload the correct certificate corresponding to this category.",
                    "confidence": 0.88
                })

        self.db.commit()
        return anomalies
