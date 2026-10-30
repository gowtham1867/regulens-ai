import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.admin_config import HolidayCalendar, WorkflowRouteTemplate
from app.models.scheduler_job import SchedulerJob
from app.services.notification_service import run_automated_escalation_scan
from app.services.audit_service import verify_audit_chain_integrity, record_audit_event

router = APIRouter(prefix="/admin-config", tags=["Admin Workflow & Rules Configuration"])


class AddHolidayRequest(BaseModel):
    region: str = "ALL"
    date: datetime
    name: str
    is_statutory: bool = True


class UpdateRouteTemplateRequest(BaseModel):
    category: str
    route_type: str
    stages: List[str]
    default_scrutiny_days: int = 15
    default_evc_days: int = 20
    default_sac_shc_days: int = 10
    default_institution_clarification_days: int = 7
    deadline_type: str = "WORKING_DAYS"


@router.get("/holidays")
def list_holidays(
    region: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(HolidayCalendar)
    if region:
        query = query.filter(HolidayCalendar.region.in_(["ALL", region]))
    return query.order_by(HolidayCalendar.date.asc()).all()


@router.post("/holidays", status_code=status.HTTP_201_CREATED)
def add_holiday(
    req: AddHolidayRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    holiday = HolidayCalendar(
        region=req.region,
        date=req.date,
        name=req.name,
        is_statutory=req.is_statutory
    )
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return holiday


@router.get("/route-templates")
def list_route_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    templates = db.query(WorkflowRouteTemplate).all()
    results = []
    for t in templates:
        results.append({
            "id": t.id,
            "category": t.category,
            "route_type": t.route_type,
            "stages": json.loads(t.stages_json) if t.stages_json else [],
            "default_scrutiny_days": t.default_scrutiny_days,
            "default_evc_days": t.default_evc_days,
            "default_sac_shc_days": t.default_sac_shc_days,
            "default_institution_clarification_days": t.default_institution_clarification_days,
            "deadline_type": t.deadline_type,
            "is_active": t.is_active,
            "version": t.version
        })
    return results


@router.post("/route-templates")
def update_route_template(
    req: UpdateRouteTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tmpl = db.query(WorkflowRouteTemplate).filter(WorkflowRouteTemplate.category == req.category).first()
    now = datetime.utcnow()
    if not tmpl:
        tmpl = WorkflowRouteTemplate(
            category=req.category,
            route_type=req.route_type,
            stages_json=json.dumps(req.stages),
            default_scrutiny_days=req.default_scrutiny_days,
            default_evc_days=req.default_evc_days,
            default_sac_shc_days=req.default_sac_shc_days,
            default_institution_clarification_days=req.default_institution_clarification_days,
            deadline_type=req.deadline_type,
            version=1
        )
        db.add(tmpl)
    else:
        tmpl.route_type = req.route_type
        tmpl.stages_json = json.dumps(req.stages)
        tmpl.default_scrutiny_days = req.default_scrutiny_days
        tmpl.default_evc_days = req.default_evc_days
        tmpl.default_sac_shc_days = req.default_sac_shc_days
        tmpl.default_institution_clarification_days = req.default_institution_clarification_days
        tmpl.deadline_type = req.deadline_type
        tmpl.version += 1
        tmpl.updated_at = now

    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.post("/trigger-escalation-scan")
def trigger_escalation_scan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = run_automated_escalation_scan(db)
    return result


@router.get("/scheduler-status")
def get_scheduler_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    jobs = db.query(SchedulerJob).all()
    return jobs
