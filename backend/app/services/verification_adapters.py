import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.document import DocumentVersion, ExtractedField
from app.models.verification import (
    VerificationSource,
    VerificationAttempt,
    VerificationOutcome,
    VerificationMethod
)


class VerificationAdapterService:
    def __init__(self, db: Session):
        self.db = db

    def verify_document_version(
        self,
        document_version_id: int,
        source_code: str,
        force_refresh: bool = False
    ) -> VerificationAttempt:
        doc_v = self.db.query(DocumentVersion).filter(DocumentVersion.id == document_version_id).first()
        if not doc_v:
            raise ValueError(f"DocumentVersion {document_version_id} not found")

        source = self.db.query(VerificationSource).filter(
            VerificationSource.source_code == source_code
        ).first()
        if not source:
            raise ValueError(f"Verification source '{source_code}' not found")

        # Extract certificate or reference number from fields
        cert_field = self.db.query(ExtractedField).filter(
            ExtractedField.document_version_id == doc_v.id,
            ExtractedField.field_key == "certificate_number"
        ).first()
        cert_no = cert_field.extracted_value if cert_field else doc_v.file_hash[:16]

        # Compute deterministic cache key for verification reuse (Section 14)
        cache_key = hashlib.sha256(
            f"{doc_v.file_hash}|{source.source_code}|{cert_no}".encode("utf-8")
        ).hexdigest()

        # Check for eligible prior verification reuse
        if not force_refresh:
            prior_valid_attempt = self.db.query(VerificationAttempt).filter(
                VerificationAttempt.cache_key == cache_key,
                VerificationAttempt.is_invalidated == False,
                VerificationAttempt.outcome.in_([VerificationOutcome.VERIFIED, VerificationOutcome.MISMATCH_DETECTED])
            ).order_by(VerificationAttempt.id.desc()).first()

            if prior_valid_attempt:
                # Reuse verified outcome!
                reused_attempt = VerificationAttempt(
                    document_version_id=doc_v.id,
                    verification_source_id=source.id,
                    certificate_number=cert_no,
                    verification_method=prior_valid_attempt.verification_method,
                    outcome=prior_valid_attempt.outcome,
                    cache_key=cache_key,
                    is_reused=True,
                    reused_from_attempt_id=prior_valid_attempt.id,
                    is_simulated=source.is_simulated,
                    evidence_payload=prior_valid_attempt.evidence_payload,
                    failure_reason=prior_valid_attempt.failure_reason,
                    request_timestamp=datetime.utcnow(),
                    response_timestamp=datetime.utcnow()
                )
                self.db.add(reused_attempt)
                self.db.commit()
                self.db.refresh(reused_attempt)
                return reused_attempt

        # Execute simulated verification adapter
        outcome, payload, failure_reason = self._execute_adapter_lookup(
            source=source,
            cert_no=cert_no,
            doc_v=doc_v
        )

        attempt = VerificationAttempt(
            document_version_id=doc_v.id,
            verification_source_id=source.id,
            certificate_number=cert_no,
            verification_method=source.verification_method,
            outcome=outcome,
            cache_key=cache_key,
            is_reused=False,
            is_simulated=source.is_simulated,
            evidence_payload=json.dumps(payload, default=str),
            failure_reason=failure_reason,
            request_timestamp=datetime.utcnow(),
            response_timestamp=datetime.utcnow()
        )
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def _execute_adapter_lookup(
        self,
        source: VerificationSource,
        cert_no: str,
        doc_v: DocumentVersion
    ) -> Tuple[VerificationOutcome, Dict[str, Any], Optional[str]]:
        """
        Deterministic mock lookup dataset clearly labelled as simulated.
        """
        clean_cert = cert_no.strip().upper()

        # Simulated outage / downtime scenario
        if "UNAVAIL" in clean_cert or not source.is_available:
            return (
                VerificationOutcome.SOURCE_UNAVAILABLE,
                {"error": "HTTP 503 Service Unavailable", "source": source.name},
                "External authority registry endpoint timed out. Retry scheduled."
            )

        # Fire Services Adapter
        if source.source_code == "STATE_FIRE_SERVICES_PORTAL":
            if any(k in clean_cert for k in ["FS-TN-2024-8841", "8841", "FIRE-2025", "NOC-2024-8849", "2026-27", "2026"]):
                return (
                    VerificationOutcome.VERIFIED,
                    {
                        "certificate_number": clean_cert,
                        "issuing_office": "Directorate of Fire and Rescue Services, State Headquarters",
                        "issued_to": "Apex Institute of Technology",
                        "validity_upto": "2026-06-30",
                        "fire_station": "Regional Fire & Emergency Station",
                        "noc_status": "AUTHENTIC_ACTIVE",
                        "registry_entry_id": f"SFRS-{hashlib.md5(clean_cert.encode()).hexdigest()[:10].upper()}",
                        "qr_verification_hash": hashlib.sha256(clean_cert.encode()).hexdigest()
                    },
                    None
                )
            elif any(k in clean_cert for k in ["FS-TN-2022-1029", "1029", "EXPIRED", "MISMATCH"]):
                return (
                    VerificationOutcome.MISMATCH_DETECTED,
                    {
                        "certificate_number": clean_cert,
                        "registry_record_found": True,
                        "registered_institution": "Sunrise Polymers Warehouse (Commercial)",
                        "recorded_expiry": "2023-01-15",
                        "status": "EXPIRED_AND_MISMATCHED_OWNER"
                    },
                    "Record retrieved from State Fire Registry belongs to a different premises and expired in 2023."
                )
            else:
                return (
                    VerificationOutcome.MANUAL_REVIEW_REQUIRED,
                    {
                        "query_reference": clean_cert,
                        "registry_queried": source.name,
                        "automated_match_found": False,
                        "requires_inspection": "Wet-ink seal, officer signature, and issuing authority letterhead"
                    },
                    f"Document reference '{clean_cert}' was not matched automatically in the State Fire & Rescue Services database. Manual officer inspection of physical stamp and seal is required."
                )

        # Land Revenue Adapter
        elif source.source_code == "STATE_REVENUE_LAND_REGISTRY":
            if any(k in clean_cert for k in ["REV-LAND", "LAND", "PATTA-1408", "TIT-2025", "1408", "42/1"]):
                return (
                    VerificationOutcome.VERIFIED,
                    {
                        "document_no": clean_cert,
                        "sub_registrar_office": "District Sub-Registrar Office",
                        "patta_number": "1408",
                        "registered_area_acres": 10.5,
                        "title_status": "CLEAR_TITLE_UNENCUMBERED",
                        "survey_nos": ["42/1A", "42/1B", "42/2"]
                    },
                    None
                )
            elif any(k in clean_cert for k in ["DISPUTE", "ENCUMBERED", "LITIGATION"]):
                return (
                    VerificationOutcome.MISMATCH_DETECTED,
                    {
                        "document_no": clean_cert,
                        "title_status": "ENCUMBERED_PENDING_LITIGATION",
                        "court_stay_order_active": True
                    },
                    "Revenue Title Registry reflects an active civil court injunction and encumbrance on parcel."
                )
            else:
                return (
                    VerificationOutcome.MANUAL_REVIEW_REQUIRED,
                    {
                        "query_reference": clean_cert,
                        "registry_queried": source.name,
                        "automated_match_found": False,
                        "recommended_action": "Verify original registered conveyance deed with Sub-Registrar seal"
                    },
                    f"Land Revenue & Title Registry could not confirm reference '{clean_cert}' through automated lookup. Manual verification by AICTE Scrutiny Officer is required."
                )

        # University Affiliation Adapter
        elif source.source_code == "AFFILIATING_UNIVERSITY_REGISTRY":
            if any(k in clean_cert for k in ["AFF-2025", "UNIV-AU-9912", "AU-9912", "ANNA-UNIV", "AFFILIATION", "SANCTION"]):
                return (
                    VerificationOutcome.VERIFIED,
                    {
                        "affiliation_code": clean_cert,
                        "university_name": "Affiliating State Technical University",
                        "academic_session": "2025-2026",
                        "approved_courses": ["Computer Science & Eng", "Electronics & Comm", "Mechanical"],
                        "sanctioned_intake": 300,
                        "standing_committee_approval": True
                    },
                    None
                )
            elif any(k in clean_cert for k in ["DISAFFILIATED", "WITHDRAWN"]):
                return (
                    VerificationOutcome.MISMATCH_DETECTED,
                    {
                        "affiliation_code": clean_cert,
                        "standing_status": "AFFILIATION_SUSPENDED"
                    },
                    "University Academic Council records show affiliation has been temporarily suspended."
                )
            else:
                return (
                    VerificationOutcome.MANUAL_REVIEW_REQUIRED,
                    {
                        "query_reference": clean_cert,
                        "registry_queried": source.name,
                        "automated_match_found": False
                    },
                    f"University Affiliation Sanction Order '{clean_cert}' could not be validated via live API. Officer manual review of Registrar signature is required."
                )

        # Any other source or document type where automated check is unconfigured:
        return (
            VerificationOutcome.MANUAL_REVIEW_REQUIRED,
            {
                "reference_no": clean_cert,
                "registry_status": "NO_AUTOMATED_API",
                "authority_type": source.authority_type,
                "queried_at": datetime.utcnow().isoformat()
            },
            f"Issuing authority '{source.name}' does not support automated API verification. AICTE Scrutiny Officer must manually inspect document authenticity."
        )

