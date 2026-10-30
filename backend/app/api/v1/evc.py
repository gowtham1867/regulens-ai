import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.evc import EVCSchedule, EVCStatus, EVCExpert
from app.services.evc_service import EVCService

router = APIRouter(prefix="/evc", tags=["EVC Inspection & Monitoring"])


class ScheduleVisitRequest(BaseModel):
    visit_date: datetime
    visit_location: str
    approved_experts: List[Dict[str, Any]]


class SubmitReportRequest(BaseModel):
    recommendation: str  # RECOMMENDED, DEFICIENT, REJECTED
    summary: str
    document_id: Optional[int] = None


@router.get("")
def list_evc_schedules(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(EVCSchedule)
    if status_filter:
        query = query.filter(EVCSchedule.status == status_filter)
    schedules = query.order_by(EVCSchedule.created_at.desc()).all()

    results = []
    for s in schedules:
        results.append({
            "id": s.id,
            "evc_no": s.evc_no,
            "application_id": s.application_id,
            "application_reference": s.application.reference_no if s.application else "N/A",
            "institution_id": s.institution_id,
            "institution_name": s.institution.name if s.institution else "N/A",
            "region": s.region,
            "status": s.status,
            "scheduled_date": s.scheduled_date.isoformat() if s.scheduled_date else None,
            "visit_location": s.visit_location,
            "conflict_check_passed": s.conflict_check_passed,
            "conflict_check_notes": s.conflict_check_notes,
            "report_recommendation": s.report_recommendation,
            "report_summary": s.report_summary,
            "proposed_panel": json.loads(s.proposed_panel) if s.proposed_panel else [],
            "approved_panel": json.loads(s.approved_panel) if s.approved_panel else [],
            "created_at": s.created_at.isoformat()
        })
    return results


@router.get("/experts")
def list_available_experts(
    region: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(EVCExpert).filter(EVCExpert.is_available == True)
    if region:
        query = query.filter(EVCExpert.region == region)
    return query.order_by(EVCExpert.active_visits_count.asc()).all()


@router.get("/{evc_id}")
def get_evc_detail(
    evc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    evc = db.query(EVCSchedule).filter(EVCSchedule.id == evc_id).first()
    if not evc:
        raise HTTPException(status_code=404, detail="EVC schedule not found")
    return {
        "id": evc.id,
        "evc_no": evc.evc_no,
        "application_id": evc.application_id,
        "application_reference": evc.application.reference_no if evc.application else "N/A",
        "institution_id": evc.institution_id,
        "institution_name": evc.institution.name if evc.institution else "N/A",
        "region": evc.region,
        "status": evc.status,
        "scheduled_date": evc.scheduled_date.isoformat() if evc.scheduled_date else None,
        "visit_location": evc.visit_location,
        "conflict_check_passed": evc.conflict_check_passed,
        "conflict_check_notes": evc.conflict_check_notes,
        "proposed_panel": json.loads(evc.proposed_panel) if evc.proposed_panel else [],
        "approved_panel": json.loads(evc.approved_panel) if evc.approved_panel else [],
        "report_recommendation": evc.report_recommendation,
        "report_summary": evc.report_summary,
        "created_at": evc.created_at.isoformat()
    }


@router.post("/queue/{application_id}")
def queue_application_for_evc(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        evc = EVCService.queue_application_for_evc(db, application_id, actor_user=current_user)
        return {"status": "QUEUED", "evc_id": evc.id, "evc_no": evc.evc_no}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{evc_id}/schedule")
def schedule_evc_visit(
    evc_id: int,
    req: ScheduleVisitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        evc = EVCService.schedule_visit(
            db=db,
            evc_id=evc_id,
            visit_date=req.visit_date,
            visit_location=req.visit_location,
            approved_experts=req.approved_experts,
            officer_user=current_user
        )
        return {"status": "SCHEDULED", "scheduled_date": evc.scheduled_date.isoformat()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{evc_id}/report")
def submit_evc_report(
    evc_id: int,
    req: SubmitReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        evc = EVCService.submit_evc_report(
            db=db,
            evc_id=evc_id,
            recommendation=req.recommendation,
            summary=req.summary,
            document_id=req.document_id,
            officer_user=current_user
        )
        return {"status": "REPORT_RECEIVED", "recommendation": evc.report_recommendation}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
