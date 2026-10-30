from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.workflow_routing import ApplicationWorkflowRouting, StageMovementHistory
from app.services.workflow_router import WorkflowRouter
from app.services.explanation_service import ExplanationService

router = APIRouter(prefix="/workflow", tags=["Workflow Routing & Stage Engine"])


class InitializeRoutingRequest(BaseModel):
    custom_route: Optional[str] = None
    custom_reason: Optional[str] = None


class AdvanceStageRequest(BaseModel):
    reason: str


class ReturnToInstitutionRequest(BaseModel):
    reason: str
    clarification_days: int = 7


class ResubmitCorrectionRequest(BaseModel):
    reason: str


@router.get("/routing/{application_id}")
def get_application_routing(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    routing = db.query(ApplicationWorkflowRouting).filter(
        ApplicationWorkflowRouting.application_id == application_id
    ).first()

    if not routing:
        # Auto-initialize if not present
        routing = WorkflowRouter.initialize_routing_for_application(
            db=db,
            application_id=application_id,
            actor_user=current_user
        )

    history = db.query(StageMovementHistory).filter(
        StageMovementHistory.application_id == application_id
    ).order_by(StageMovementHistory.id.asc()).all()

    return {
        "id": routing.id,
        "application_id": routing.application_id,
        "route_type": routing.route_type,
        "current_stage": routing.current_stage,
        "stage_entry_at": routing.stage_entry_at.isoformat() if routing.stage_entry_at else None,
        "stage_deadline": routing.stage_deadline.isoformat() if routing.stage_deadline else None,
        "processing_status": routing.processing_status,
        "is_completed": routing.is_completed,
        "next_eligible_stage": routing.next_eligible_stage,
        "routing_reason": routing.routing_reason,
        "assigned_committee": routing.assigned_committee,
        "stage_history": [
            {
                "id": h.id,
                "from_stage": h.from_stage,
                "to_stage": h.to_stage,
                "action": h.action,
                "reason": h.reason,
                "officer_name": h.officer.name if h.officer else "System Automation",
                "timestamp": h.created_at.isoformat()
            }
            for h in history
        ]
    }


@router.get("/routing/{application_id}/why")
def explain_routing_why(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        return ExplanationService.explain_application_routing(db, application_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/routing/{application_id}/initialize")
def initialize_routing(
    application_id: int,
    req: InitializeRoutingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        routing = WorkflowRouter.initialize_routing_for_application(
            db=db,
            application_id=application_id,
            custom_route=req.custom_route,
            custom_reason=req.custom_reason,
            actor_user=current_user
        )
        return {"status": "INITIALIZED", "route_type": routing.route_type, "current_stage": routing.current_stage}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/routing/{application_id}/advance")
def advance_workflow_stage(
    application_id: int,
    req: AdvanceStageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        routing = WorkflowRouter.advance_stage(
            db=db,
            application_id=application_id,
            reason=req.reason,
            actor_user=current_user
        )
        return {
            "status": "ADVANCED",
            "current_stage": routing.current_stage,
            "next_eligible_stage": routing.next_eligible_stage,
            "processing_status": routing.processing_status
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/routing/{application_id}/return")
def return_to_institution(
    application_id: int,
    req: ReturnToInstitutionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        routing = WorkflowRouter.return_to_institution(
            db=db,
            application_id=application_id,
            reason=req.reason,
            actor_user=current_user,
            clarification_days=req.clarification_days
        )
        return {
            "status": "RETURNED_FOR_CLARIFICATION",
            "current_stage": routing.current_stage,
            "processing_status": routing.processing_status
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/routing/{application_id}/resubmit")
def resubmit_corrections(
    application_id: int,
    req: ResubmitCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        routing = WorkflowRouter.resume_after_institution_resubmission(
            db=db,
            application_id=application_id,
            reason=req.reason,
            actor_user=current_user
        )
        return {
            "status": "RE_SCRUTINY_RESUMED",
            "current_stage": routing.current_stage,
            "processing_status": routing.processing_status
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
