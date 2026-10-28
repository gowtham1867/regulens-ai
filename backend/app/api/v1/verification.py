from typing import List, Optional
from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.document import Document, DocumentVersion, ExtractedField
from app.models.finding import ValidationFinding, FindingStatus
from app.models.verification import (
    VerificationSource,
    VerificationAttempt,
    VerificationOutcome,
    VerificationMethod
)
from app.schemas.all_schemas import (
    VerificationSourceResponse,
    VerificationAttemptResponse,
    ManualVerificationRequest
)
from app.services.verification_adapters import VerificationAdapterService
from app.services.audit_service import record_audit_event

router = APIRouter(tags=["Issuing Authority Verification"])


@router.get("/verification-sources", response_model=List[VerificationSourceResponse])
def list_verification_sources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sources = db.query(VerificationSource).filter(VerificationSource.is_active == True).all()
    return sources


def _resolve_source_for_doc(doc: Document) -> str:
    """Intelligently map document type to the corresponding official registry adapter."""
    dt = doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type).upper()
    if "FIRE" in dt:
        return "STATE_FIRE_SERVICES_PORTAL"
    elif "LAND" in dt or "TITLE" in dt or "REVENUE" in dt:
        return "STATE_REVENUE_LAND_REGISTRY"
    elif "AFFILIATION" in dt or "UNIVERSITY" in dt:
        return "AFFILIATING_UNIVERSITY_REGISTRY"
    return "STATE_FIRE_SERVICES_PORTAL"


@router.post("/documents/{document_id}/verify", response_model=VerificationAttemptResponse)
def verify_document_with_issuer(
    document_id: int,
    source_code: Optional[str] = Query(None, description="Verification source adapter code or 'AUTO'"),
    force_refresh: bool = Query(False, description="Bypass verification cache"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    latest_v = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc.id
    ).order_by(DocumentVersion.version_number.desc()).first()
    if not latest_v:
        raise HTTPException(status_code=400, detail="Document has no uploaded versions to verify")

    resolved_source = source_code
    if not resolved_source or resolved_source.strip().upper() == "AUTO":
        resolved_source = _resolve_source_for_doc(doc)

    service = VerificationAdapterService(db)
    attempt = service.verify_document_version(
        document_version_id=latest_v.id,
        source_code=resolved_source,
        force_refresh=force_refresh
    )

    record_audit_event(
        db=db,
        action="VERIFY_DOCUMENT_ISSUER",
        entity_type="DOCUMENT_VERSION",
        entity_id=str(latest_v.id),
        actor=current_user,
        details=f"Verification executed via '{attempt.source.name}'. Outcome: {attempt.outcome.value}. Reused: {attempt.is_reused}."
    )

    return {
        "id": attempt.id,
        "source_name": attempt.source.name,
        "authority_type": attempt.source.authority_type,
        "certificate_number": attempt.certificate_number,
        "verification_method": attempt.verification_method.value,
        "outcome": attempt.outcome.value,
        "is_reused": attempt.is_reused,
        "is_simulated": attempt.is_simulated,
        "failure_reason": attempt.failure_reason,
        "evidence_payload": attempt.evidence_payload,
        "request_timestamp": attempt.request_timestamp,
        "response_timestamp": attempt.response_timestamp
    }


@router.post("/documents/{document_id}/manual-verify", response_model=VerificationAttemptResponse)
def manual_officer_verify(
    document_id: int,
    req: ManualVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dedicated workflow allowing an authorized AICTE Scrutiny Officer
    to record a manual verification outcome with audit trail and notes.
    """
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only authorized AICTE Officers and Administrators can record official manual authority verifications."
        )

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    latest_v = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc.id
    ).order_by(DocumentVersion.version_number.desc()).first()
    if not latest_v:
        raise HTTPException(status_code=400, detail="Document has no uploaded versions to verify")

    # Find or create manual verification source
    manual_source = db.query(VerificationSource).filter(
        VerificationSource.source_code == "AICTE_OFFICER_MANUAL_SCRUTINY"
    ).first()
    if not manual_source:
        manual_source = VerificationSource(
            source_code="AICTE_OFFICER_MANUAL_SCRUTINY",
            name="AICTE Officer Manual Physical Scrutiny",
            authority_type="AICTE_SCRUTINY_OFFICER",
            verification_method=VerificationMethod.MANUAL_EVIDENCE,
            is_simulated=False,
            simulated_badge_label="OFFICER MANUAL INSPECTION",
            is_active=True,
            is_available=True
        )
        db.add(manual_source)
        db.commit()
        db.refresh(manual_source)

    # Determine outcome
    outcome_map = {
        "VERIFIED": VerificationOutcome.VERIFIED,
        "MISMATCH_DETECTED": VerificationOutcome.MISMATCH_DETECTED,
        "MANUAL_REVIEW_REQUIRED": VerificationOutcome.MANUAL_REVIEW_REQUIRED,
        "SOURCE_UNAVAILABLE": VerificationOutcome.SOURCE_UNAVAILABLE,
    }
    chosen_outcome = outcome_map.get(req.outcome.strip().upper(), VerificationOutcome.VERIFIED)

    cert_no = req.certificate_number
    if not cert_no:
        cert_field = db.query(ExtractedField).filter(
            ExtractedField.document_version_id == latest_v.id,
            ExtractedField.field_key.in_(["certificate_number", "noc_number", "patta_number"])
        ).first()
        cert_no = cert_field.extracted_value if cert_field else latest_v.file_hash[:16]

    evidence = {
        "officer_name": current_user.full_name,
        "officer_email": current_user.email,
        "designation": current_user.designation or "AICTE Scrutiny Officer",
        "issuing_authority_attested": req.issuing_authority or "Competent State Authority",
        "notes": req.notes.strip(),
        "verified_at": datetime.utcnow().isoformat(),
        "inspection_type": "PHYSICAL_SEAL_AND_SIGNATURE_VERIFICATION"
    }

    attempt = VerificationAttempt(
        document_version_id=latest_v.id,
        verification_source_id=manual_source.id,
        certificate_number=cert_no,
        verification_method=VerificationMethod.MANUAL_EVIDENCE,
        outcome=chosen_outcome,
        is_reused=False,
        is_simulated=False,
        evidence_payload=json.dumps(evidence),
        failure_reason=req.notes if chosen_outcome != VerificationOutcome.VERIFIED else None,
        request_timestamp=datetime.utcnow(),
        response_timestamp=datetime.utcnow()
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # Record tamper-evident audit event
    record_audit_event(
        db=db,
        action="OFFICER_MANUAL_AUTHORITY_VERIFICATION",
        entity_type="DOCUMENT_VERSION",
        entity_id=str(latest_v.id),
        actor=current_user,
        details=f"Officer {current_user.full_name} attested authority verification for '{doc.title}'. Outcome: {chosen_outcome.value}. Notes: {req.notes[:100]}"
    )

    return {
        "id": attempt.id,
        "source_name": manual_source.name,
        "authority_type": manual_source.authority_type,
        "certificate_number": attempt.certificate_number,
        "verification_method": attempt.verification_method.value,
        "outcome": attempt.outcome.value,
        "is_reused": attempt.is_reused,
        "is_simulated": attempt.is_simulated,
        "failure_reason": attempt.failure_reason,
        "evidence_payload": attempt.evidence_payload,
        "request_timestamp": attempt.request_timestamp,
        "response_timestamp": attempt.response_timestamp
    }


@router.get("/documents/{document_id}/verification-history", response_model=List[VerificationAttemptResponse])
def get_document_verification_history(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    attempts = db.query(VerificationAttempt).join(DocumentVersion).filter(
        DocumentVersion.document_id == document_id
    ).order_by(VerificationAttempt.id.desc()).all()

    results = []
    for att in attempts:
        results.append({
            "id": att.id,
            "source_name": att.source.name if att.source else "Registry Source",
            "authority_type": att.source.authority_type if att.source else "OFFICIAL_AUTHORITY",
            "certificate_number": att.certificate_number,
            "verification_method": att.verification_method.value,
            "outcome": att.outcome.value,
            "is_reused": att.is_reused,
            "is_simulated": att.is_simulated,
            "failure_reason": att.failure_reason,
            "evidence_payload": att.evidence_payload,
            "request_timestamp": att.request_timestamp,
            "response_timestamp": att.response_timestamp
        })
    return results

