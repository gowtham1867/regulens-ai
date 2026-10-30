from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.undertaking import TimeBoundUndertaking, UndertakingStatus
from app.models.institution import InstitutionMembership
from app.services.undertaking_service import UndertakingService

router = APIRouter(prefix="/undertakings", tags=["Time-Bound Undertakings"])


class CreateUndertakingRequest(BaseModel):
    application_id: int
    condition_title: str
    condition_description: str
    statutory_deadline_months: int = 6
    aph_clause: str = "APH 2024-27 Clause 7.12"


class SubmitEvidenceRequest(BaseModel):
    evidence_description: str
    document_id: Optional[int] = None


class ReviewComplianceRequest(BaseModel):
    is_compliant: bool
    review_notes: str


@router.get("")
def list_undertakings(
    institution_id: Optional[int] = None,
    application_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(TimeBoundUndertaking)

    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership:
            return []
        query = query.filter(TimeBoundUndertaking.institution_id == membership.institution_id)
    elif institution_id:
        query = query.filter(TimeBoundUndertaking.institution_id == institution_id)

    if application_id:
        query = query.filter(TimeBoundUndertaking.application_id == application_id)
    if status_filter:
        query = query.filter(TimeBoundUndertaking.status == status_filter)

    uts = query.order_by(TimeBoundUndertaking.due_date.asc()).all()

    now = datetime.utcnow()
    results = []
    for u in uts:
        days_rem = (u.due_date - now).days
        results.append({
            "id": u.id,
            "undertaking_no": u.undertaking_no,
            "application_id": u.application_id,
            "application_reference": u.application.reference_no if u.application else "N/A",
            "institution_id": u.institution_id,
            "institution_name": u.institution.name if u.institution else "N/A",
            "condition_title": u.condition_title,
            "condition_description": u.condition_description,
            "aph_clause": u.aph_clause,
            "statutory_deadline_months": u.statutory_deadline_months,
            "due_date": u.due_date.isoformat(),
            "days_remaining": days_rem,
            "status": u.status,
            "evidence_submission_date": u.evidence_submission_date.isoformat() if u.evidence_submission_date else None,
            "evidence_description": u.evidence_description,
            "evidence_document_id": u.evidence_document_id,
            "officer_review_notes": u.officer_review_notes,
            "reviewed_at": u.reviewed_at.isoformat() if u.reviewed_at else None,
            "created_at": u.created_at.isoformat()
        })
    return results


@router.post("", status_code=status.HTTP_201_CREATED)
def create_undertaking(
    req: CreateUndertakingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        ut = UndertakingService.create_undertaking(
            db=db,
            application_id=req.application_id,
            condition_title=req.condition_title,
            condition_description=req.condition_description,
            statutory_deadline_months=req.statutory_deadline_months,
            aph_clause=req.aph_clause,
            actor_user=current_user
        )
        return {"status": "CREATED", "undertaking_id": ut.id, "undertaking_no": ut.undertaking_no}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{undertaking_id}/submit-evidence")
def submit_evidence(
    undertaking_id: int,
    req: SubmitEvidenceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        ut = UndertakingService.submit_compliance_evidence(
            db=db,
            undertaking_id=undertaking_id,
            evidence_description=req.evidence_description,
            document_id=req.document_id,
            institution_user=current_user
        )
        return {"status": "EVIDENCE_SUBMITTED", "undertaking_id": ut.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{undertaking_id}/review")
def review_compliance(
    undertaking_id: int,
    req: ReviewComplianceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        ut = UndertakingService.review_compliance(
            db=db,
            undertaking_id=undertaking_id,
            is_compliant=req.is_compliant,
            review_notes=req.review_notes,
            officer_user=current_user
        )
        return {"status": "REVIEWED", "compliance_status": ut.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
