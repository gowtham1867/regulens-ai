from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.application import Application, ApplicationStatus, ApplicationStatusHistory
from app.models.finding import ValidationFinding, FindingStatus
from app.models.workflow import (
    OfficerReview,
    WorkflowDecision,
    DecisionType,
    ClarificationRequest,
    ClarificationStatus
)
from app.schemas.all_schemas import (
    OfficerReviewCreate,
    WorkflowDecisionCreate,
    WorkflowDecisionResponse
)
from app.services.audit_service import record_audit_event
from app.services.notification_service import create_notification, notify_institution_users
from app.models.institution import InstitutionMembership

router = APIRouter(tags=["Officer Scrutiny & Decisions"])


@router.post("/applications/{application_id}/reviews")
def add_officer_review_note(
    application_id: int,
    review_in: OfficerReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Only authorized AICTE Officers can record review notes")

    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    review = OfficerReview(
        application_id=application_id,
        officer_id=current_user.id,
        review_stage=review_in.review_stage,
        review_notes=review_in.review_notes,
        recommended_action=review_in.recommended_action,
        created_at=datetime.utcnow()
    )
    db.add(review)
    db.commit()

    record_audit_event(
        db=db,
        action="ADD_OFFICER_REVIEW_NOTE",
        entity_type="APPLICATION",
        entity_id=str(application_id),
        actor=current_user,
        details=f"Officer {current_user.full_name} added scrutiny note: '{review_in.review_notes[:60]}...'"
    )

    return {"message": "Review note recorded successfully", "review_id": review.id}


@router.get("/applications/{application_id}/reviews")
def get_application_reviews(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    reviews = db.query(OfficerReview).filter(
        OfficerReview.application_id == application_id
    ).order_by(OfficerReview.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "officer_name": r.officer.full_name if r.officer else "Scrutiny Officer",
            "review_stage": r.review_stage,
            "review_notes": r.review_notes,
            "recommended_action": r.recommended_action,
            "created_at": r.created_at
        }
        for r in reviews
    ]


@router.get("/applications/{application_id}/decisions", response_model=List[WorkflowDecisionResponse])
def get_application_decisions(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    decisions = db.query(WorkflowDecision).filter(
        WorkflowDecision.application_id == application_id
    ).order_by(WorkflowDecision.decided_at.desc()).all()

    return [
        {
            "id": d.id,
            "decision": d.decision.value if hasattr(d.decision, "value") else str(d.decision),
            "justification": d.justification,
            "officer_name": d.officer.full_name if d.officer else "AICTE Officer",
            "rejection_reason": d.rejection_reason,
            "is_override": d.is_override,
            "override_reason": d.override_reason,
            "decided_at": d.decided_at
        }
        for d in decisions
    ]


@router.post("/applications/{application_id}/decisions", response_model=WorkflowDecisionResponse)
def record_final_decision(
    application_id: int,
    decision_in: WorkflowDecisionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enforces controlled regulatory decision state machine.
    Requires human officer authorization.
    Handles:
      - APPROVE (requires resolution or override for critical findings)
      - REJECT (mandates explicit rejection reason and detailed explanation)
      - REQUEST_CORRECTION / RETURN (transitions to CLARIFICATION_REQUESTED and logs clarification)
      - REQUEST_DOCUMENTS (transitions to CLARIFICATION_REQUESTED and specifies required docs)
      - UNDER_REVIEW (places application in active review)
    Notifies strictly the affiliated institution users and records audit trails.
    """
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Only authorized AICTE Officers can record regulatory decisions")

    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    old_status = app.status.value if hasattr(app.status, "value") else str(app.status)
    decision_action = decision_in.decision.upper()

    # 1. Validation & state transition based on decision action
    if decision_action == "APPROVE":
        active_critical_failures = db.query(ValidationFinding).filter(
            ValidationFinding.application_id == application_id,
            ValidationFinding.is_active == True,
            ValidationFinding.status == FindingStatus.FAILED,
            ValidationFinding.severity == "CRITICAL"
        ).count()

        if active_critical_failures > 0 and not decision_in.is_override:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot APPROVE application with {active_critical_failures} unresolved critical finding(s). Resolution or documented authorized override is required."
            )
        if decision_in.is_override and not (decision_in.override_reason and decision_in.override_reason.strip()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Documented override reason is mandatory when approving with active critical findings."
            )

        app.status = ApplicationStatus.APPROVED
        notif_type = "SUCCESS"
        notif_title = f"Application Approved: {app.reference_no}"
        notif_message = (
            f"Official AICTE Scrutiny for Application {app.reference_no} ({app.institution.name if app.institution else 'Institution'}) "
            f"has been APPROVED."
        )
        notif_details = decision_in.justification

    elif decision_action == "REJECT":
        if not decision_in.rejection_reason or not decision_in.rejection_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection reason is strictly required when rejecting an application."
            )
        if not decision_in.justification or len(decision_in.justification.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A detailed justification/explanation of at least 10 characters is required for rejection."
            )

        app.status = ApplicationStatus.REJECTED
        notif_type = "ERROR"
        notif_title = f"Application Rejected: {app.reference_no}"
        notif_message = (
            f"Application {app.reference_no} has been rejected by AICTE Scrutiny Officers. "
            f"Reason: {decision_in.rejection_reason}"
        )
        rule_info = f"\nAffected Rule IDs: {', '.join(map(str, decision_in.rule_ids))}" if decision_in.rule_ids else ""
        doc_info = f"\nAffected Document IDs: {', '.join(map(str, decision_in.document_ids))}" if decision_in.document_ids else ""
        notif_details = f"Rejection Category: {decision_in.rejection_reason}\n\nDetailed Explanation:\n{decision_in.justification}{rule_info}{doc_info}"

    elif decision_action in ["REQUEST_CORRECTION", "RETURN"]:
        if not decision_in.justification or len(decision_in.justification.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide detailed instructions for the requested corrections."
            )

        app.status = ApplicationStatus.CLARIFICATION_REQUESTED
        notif_type = "WARNING"
        notif_title = f"Action Required: Correction Requested for {app.reference_no}"
        notif_message = (
            f"AICTE Scrutiny Officers have returned Application {app.reference_no} requesting corrections/clarifications. "
            f"Please review the required changes and upload corrected documents."
        )
        notif_details = decision_in.justification

        # Create ClarificationRequest entry
        relevant_doc_id = decision_in.document_ids[0] if (decision_in.document_ids and len(decision_in.document_ids) > 0) else None
        relevant_find_id = decision_in.rule_ids[0] if (decision_in.rule_ids and len(decision_in.rule_ids) > 0) else None
        
        clarification_req = ClarificationRequest(
            application_id=app.id,
            requesting_officer_id=current_user.id,
            subject=f"Correction Requested: {app.reference_no}",
            requested_information=decision_in.justification,
            instructions_for_correction=decision_in.justification,
            relevant_finding_id=relevant_find_id,
            relevant_document_id=relevant_doc_id,
            status=ClarificationStatus.OPEN,
            due_date=datetime.utcnow() + timedelta(days=7),
            created_at=datetime.utcnow()
        )
        db.add(clarification_req)

    elif decision_action == "REQUEST_DOCUMENTS":
        if not decision_in.justification or len(decision_in.justification.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please specify which additional documents are required from the institution."
            )

        app.status = ApplicationStatus.CLARIFICATION_REQUESTED
        notif_type = "WARNING"
        notif_title = f"Additional Documents Required: {app.reference_no}"
        notif_message = (
            f"AICTE Scrutiny Officers have requested additional documentation for Application {app.reference_no}. "
            f"Please upload the required evidence promptly."
        )
        notif_details = decision_in.justification

        clarification_req = ClarificationRequest(
            application_id=app.id,
            requesting_officer_id=current_user.id,
            subject=f"Additional Documents Required: {app.reference_no}",
            requested_information=decision_in.justification,
            instructions_for_correction="Upload the requested missing documents under the Documents tab.",
            status=ClarificationStatus.OPEN,
            due_date=datetime.utcnow() + timedelta(days=7),
            created_at=datetime.utcnow()
        )
        db.add(clarification_req)

    elif decision_action == "UNDER_REVIEW":
        app.status = ApplicationStatus.UNDER_REVIEW
        notif_type = "INFO"
        notif_title = f"Application Under Review: {app.reference_no}"
        notif_message = f"Application {app.reference_no} is actively being scrutinized by AICTE officers."
        notif_details = decision_in.justification or "Scrutiny review is in progress."

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown decision action '{decision_in.decision}'. Expected APPROVE, REJECT, REQUEST_CORRECTION, REQUEST_DOCUMENTS, or UNDER_REVIEW."
        )

    # 2. Persist WorkflowDecision record
    decision_record = WorkflowDecision(
        application_id=application_id,
        officer_id=current_user.id,
        decision=decision_action,
        justification=decision_in.justification,
        rejection_reason=decision_in.rejection_reason if decision_action == "REJECT" else None,
        is_override=decision_in.is_override,
        override_reason=decision_in.override_reason if decision_in.is_override else None,
        decided_at=datetime.utcnow()
    )
    db.add(decision_record)

    # 3. Record ApplicationStatusHistory entry
    status_history = ApplicationStatusHistory(
        application_id=application_id,
        from_status=old_status,
        to_status=app.status.value,
        changed_by_user_id=current_user.id,
        reason=decision_in.rejection_reason if decision_action == "REJECT" else decision_in.justification,
        created_at=datetime.utcnow()
    )
    db.add(status_history)

    # Commit all state changes atomically
    db.commit()
    db.refresh(decision_record)

    # 4. Record comprehensive audit event
    record_audit_event(
        db=db,
        action=f"WORKFLOW_DECISION_{decision_action}",
        entity_type="APPLICATION",
        entity_id=str(application_id),
        actor=current_user,
        before_state={"status": old_status},
        after_state={
            "status": app.status.value,
            "decision": decision_action,
            "rejection_reason": decision_in.rejection_reason,
            "override": decision_in.is_override
        },
        details=f"Decision '{decision_action}' recorded by {current_user.full_name} ({current_user.email}). Justification: {decision_in.justification}"
    )

    # 5. Notify strictly affiliated institution users (never leak across institutions)
    notify_institution_users(
        db=db,
        institution_id=app.institution_id,
        title=notif_title,
        message=notif_message,
        notification_type=notif_type,
        link=f"/applications/{app.id}",
        application_id=app.id,
        action_type=decision_action,
        details=notif_details
    )

    return {
        "id": decision_record.id,
        "decision": decision_record.decision.value if hasattr(decision_record.decision, "value") else str(decision_record.decision),
        "justification": decision_record.justification,
        "officer_name": current_user.full_name,
        "rejection_reason": decision_record.rejection_reason,
        "is_override": decision_record.is_override,
        "override_reason": decision_record.override_reason,
        "decided_at": decision_record.decided_at
    }


