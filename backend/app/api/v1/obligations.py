from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.obligation import Obligation, ObligationStatus
from app.models.institution import InstitutionMembership
from app.services.obligation_service import (
    create_obligation,
    get_obligations_for_institution,
    get_obligations_for_application,
    get_officer_inbox_obligations
)
from app.services.clock_engine import ClockEngine
from app.services.explanation_service import ExplanationService

router = APIRouter(prefix="/obligations", tags=["Obligations & Promise Ledger"])


class CreateObligationRequest(BaseModel):
    institution_id: int
    application_id: Optional[int] = None
    obligation_type: str
    title: str
    description: str
    responsible_entity: str
    responsible_role: str = "AICTE_OFFICER"
    responsible_post: str = "Scrutiny Cell"
    source_event: str = "MANUAL_CREATION"
    aph_clause: str = "APH 2024-27 Clause 2.3"
    is_aph_verified: bool = True
    configured_days: int = 30
    deadline_type: str = "WORKING_DAYS"
    notes: Optional[str] = None


class PauseClockRequest(BaseModel):
    reason: str
    pause_state: str = "PAUSED_INSTITUTION"


class ResumeClockRequest(BaseModel):
    reason: str


class ExtensionRequest(BaseModel):
    additional_days: int
    reason: str


class CompleteObligationRequest(BaseModel):
    reason: str
    evidence_refs: Optional[str] = None


@router.get("")
def list_obligations(
    institution_id: Optional[int] = None,
    application_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Obligation)

    # Institution isolation
    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership:
            return []
        query = query.filter(Obligation.institution_id == membership.institution_id)
    elif institution_id:
        query = query.filter(Obligation.institution_id == institution_id)

    if application_id:
        query = query.filter(Obligation.application_id == application_id)
    if status_filter:
        query = query.filter(Obligation.status == status_filter)

    obls = query.order_by(Obligation.due_date.asc()).all()

    now = datetime.utcnow()
    results = []
    for obl in obls:
        days_rem = (obl.due_date - now).days
        results.append({
            "id": obl.id,
            "obligation_no": obl.obligation_no,
            "institution_id": obl.institution_id,
            "institution_name": obl.institution.name if obl.institution else "N/A",
            "application_id": obl.application_id,
            "obligation_type": obl.obligation_type,
            "title": obl.title,
            "description": obl.description,
            "responsible_entity": obl.responsible_entity,
            "responsible_role": obl.responsible_role,
            "responsible_post": obl.responsible_post,
            "aph_clause": obl.aph_clause,
            "is_aph_verified": obl.is_aph_verified,
            "configured_days": obl.configured_days,
            "deadline_type": obl.deadline_type,
            "start_date": obl.start_date.isoformat(),
            "due_date": obl.due_date.isoformat(),
            "days_remaining": days_rem,
            "status": obl.status,
            "clock_state": obl.clock_state,
            "total_paused_days": obl.total_paused_days,
            "approved_extension_days": obl.approved_extension_days,
            "escalation_level": obl.escalation_level,
            "verification_status": obl.verification_status,
            "created_at": obl.created_at.isoformat()
        })
    return results


@router.get("/officer-inbox/today")
def get_today_inbox(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Officer Daily Inbox — Today's 10 with transparent priority reasons."""
    return get_officer_inbox_obligations(db, limit=limit)


@router.get("/{obligation_id}")
def get_obligation(
    obligation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    obl = db.query(Obligation).filter(Obligation.id == obligation_id).first()
    if not obl:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return obl


@router.get("/{obligation_id}/why")
def explain_obligation_why(
    obligation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Phase 5: The "Why?" explainability breakdown.
    Returns mathematical deadline derivation, holidays excluded, paused intervals,
    regulatory clauses, and SHA-256 cryptographic provenance.
    """
    try:
        return ExplanationService.explain_obligation(db, obligation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_new_obligation(
    req: CreateObligationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    obl = create_obligation(
        db=db,
        institution_id=req.institution_id,
        application_id=req.application_id,
        obligation_type=req.obligation_type,
        title=req.title,
        description=req.description,
        responsible_entity=req.responsible_entity,
        responsible_role=req.responsible_role,
        responsible_post=req.responsible_post,
        source_event=req.source_event,
        aph_clause=req.aph_clause,
        is_aph_verified=req.is_aph_verified,
        deadline_type=req.deadline_type,
        configured_days=req.configured_days,
        notes=req.notes,
        actor_user=current_user
    )
    return {"status": "SUCCESS", "obligation_id": obl.id, "obligation_no": obl.obligation_no}


@router.post("/{obligation_id}/pause")
def pause_clock(
    obligation_id: int,
    req: PauseClockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        obl = ClockEngine.pause_obligation_clock(
            db=db,
            obligation_id=obligation_id,
            reason=req.reason,
            actor=current_user.email,
            pause_state=req.pause_state
        )
        return {"status": "PAUSED", "clock_state": obl.clock_state, "obligation_no": obl.obligation_no}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{obligation_id}/resume")
def resume_clock(
    obligation_id: int,
    req: ResumeClockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        obl = ClockEngine.resume_obligation_clock(
            db=db,
            obligation_id=obligation_id,
            reason=req.reason,
            actor=current_user.email
        )
        return {"status": "RUNNING", "clock_state": obl.clock_state, "new_due_date": obl.due_date.isoformat()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{obligation_id}/extension")
def grant_extension(
    obligation_id: int,
    req: ExtensionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        obl = ClockEngine.grant_extension(
            db=db,
            obligation_id=obligation_id,
            additional_days=req.additional_days,
            reason=req.reason,
            approved_by=current_user.name or current_user.email
        )
        return {"status": "EXTENDED", "new_due_date": obl.due_date.isoformat(), "approved_extension_days": obl.approved_extension_days}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{obligation_id}/complete")
def complete_obligation(
    obligation_id: int,
    req: CompleteObligationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        obl = ClockEngine.complete_obligation(
            db=db,
            obligation_id=obligation_id,
            reason=req.reason,
            actor=current_user.email,
            evidence_refs=req.evidence_refs
        )
        return {"status": "MET", "clock_state": obl.clock_state, "completion_date": obl.completion_date.isoformat()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
