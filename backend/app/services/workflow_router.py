from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus, ApplicationCategory
from app.models.workflow_routing import (
    ApplicationWorkflowRouting,
    ApplicationRouteType,
    WorkflowStage,
    StageMovementHistory,
)
from app.models.obligation import Obligation, ObligationType, ResponsibleRole
from app.models.user import User
from app.models.notification import Notification
from app.services.obligation_service import create_obligation
from app.services.clock_engine import ClockEngine
from app.services.audit_service import record_audit_event


# Standard Stage Progression Paths for each Route
ROUTE_STAGE_SEQUENCES: Dict[str, List[str]] = {
    ApplicationRouteType.ONLY_SCRUTINY.value: [
        WorkflowStage.SCRUTINY_STAGE.value,
        WorkflowStage.FINAL_APPROVAL.value,
        WorkflowStage.CLOSED.value,
    ],
    ApplicationRouteType.SCRUTINY_EVC.value: [
        WorkflowStage.SCRUTINY_STAGE.value,
        WorkflowStage.EVC_STAGE.value,
        WorkflowStage.FINAL_APPROVAL.value,
        WorkflowStage.CLOSED.value,
    ],
    ApplicationRouteType.EVC_SAC_SHC.value: [
        WorkflowStage.EVC_STAGE.value,
        WorkflowStage.SAC_SHC_STAGE.value,
        WorkflowStage.FINAL_APPROVAL.value,
        WorkflowStage.CLOSED.value,
    ],
    ApplicationRouteType.ONLY_EVC.value: [
        WorkflowStage.EVC_STAGE.value,
        WorkflowStage.FINAL_APPROVAL.value,
        WorkflowStage.CLOSED.value,
    ],
    ApplicationRouteType.FULL_SCRUTINY_EVC_SAC.value: [
        WorkflowStage.SCRUTINY_STAGE.value,
        WorkflowStage.EVC_STAGE.value,
        WorkflowStage.SAC_SHC_STAGE.value,
        WorkflowStage.FINAL_APPROVAL.value,
        WorkflowStage.CLOSED.value,
    ],
}


class WorkflowRouter:
    """
    Configurable state machine and workflow routing engine for AICTE applications.
    Complies with Phase 3 specifications.
    """

    @classmethod
    def determine_route_for_application(cls, application: Application) -> Tuple[str, str]:
        """
        Determines the statutory route and justification based on application category & parameters.
        """
        cat = application.category
        if cat == ApplicationCategory.NEW_INSTITUTION:
            return (
                ApplicationRouteType.FULL_SCRUTINY_EVC_SAC.value,
                "APH 2024-27 Chapter I: New Institution establishment mandates Scrutiny, Physical EVC inspection, and SAC review before final Letter of Approval."
            )
        elif cat in [ApplicationCategory.CHANGE_OF_SITE, ApplicationCategory.INCREASE_IN_INTAKE]:
            return (
                ApplicationRouteType.SCRUTINY_EVC.value,
                "APH 2024-27 Chapter II: Infrastructure or intake changes mandate Document Scrutiny followed by physical Expert Visit Committee verification."
            )
        elif cat == ApplicationCategory.INTRODUCTION_OF_NEW_COURSE:
            return (
                ApplicationRouteType.ONLY_SCRUTINY.value,
                "APH 2024-27 Chapter II: Introduction of new emerging courses in existing accredited programs is evaluated via Scrutiny Committee."
            )
        else:
            # Default EXTENSION_OF_APPROVAL
            return (
                ApplicationRouteType.ONLY_SCRUTINY.value,
                "APH 2024-27 Chapter I: Standard Extension of Approval (EoA) is processed via Scrutiny Committee and self-disclosure verification."
            )

    @classmethod
    def initialize_routing_for_application(
        cls,
        db: Session,
        application_id: int,
        custom_route: Optional[str] = None,
        custom_reason: Optional[str] = None,
        actor_user: Optional[User] = None
    ) -> ApplicationWorkflowRouting:
        """
        Initializes the workflow route and stage tracking for an application.
        """
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            raise ValueError(f"Application {application_id} not found.")

        existing = db.query(ApplicationWorkflowRouting).filter(
            ApplicationWorkflowRouting.application_id == application_id
        ).first()
        if existing:
            return existing

        if custom_route:
            route_type = custom_route
            routing_reason = custom_reason or "Manually assigned statutory route by Competent Authority."
        else:
            route_type, routing_reason = cls.determine_route_for_application(application)

        sequence = ROUTE_STAGE_SEQUENCES.get(route_type, ROUTE_STAGE_SEQUENCES[ApplicationRouteType.ONLY_SCRUTINY.value])
        first_stage = sequence[0]
        next_stage = sequence[1] if len(sequence) > 1 else None

        now = datetime.utcnow()
        routing = ApplicationWorkflowRouting(
            application_id=application.id,
            route_type=route_type,
            current_stage=first_stage,
            stage_entry_at=now,
            stage_deadline=now + timedelta(days=15),
            assigned_officer_id=application.assigned_officer_id,
            assigned_committee="Scrutiny Committee (Regional)",
            processing_status="IN_PROGRESS",
            is_completed=False,
            next_eligible_stage=next_stage,
            routing_reason=routing_reason
        )
        db.add(routing)
        db.flush()

        # Record initial stage history
        history = StageMovementHistory(
            application_id=application.id,
            routing_id=routing.id,
            from_stage=None,
            to_stage=first_stage,
            action="INITIALIZE",
            reason=f"Workflow initialized on route {route_type}. {routing_reason}",
            officer_id=actor_user.id if actor_user else None,
            created_at=now
        )
        db.add(history)

        # Create initial Scrutiny Obligation in Promise Ledger
        create_obligation(
            db=db,
            institution_id=application.institution_id,
            application_id=application.id,
            obligation_type=ObligationType.APPLICATION_SCRUTINY.value,
            title=f"Application Scrutiny: {application.reference_no}",
            description=f"Statutory scrutiny review for {application.title} under {route_type} route.",
            responsible_entity="Scrutiny Cell",
            responsible_role=ResponsibleRole.AICTE_OFFICER.value,
            responsible_post="Scrutiny Officer",
            source_event="APPLICATION_SUBMISSION",
            aph_clause="APH 2024-27 Clause 2.3",
            is_aph_verified=True,
            deadline_type="WORKING_DAYS",
            configured_days=15,
            actor_user=actor_user
        )

        db.commit()
        db.refresh(routing)
        return routing

    @classmethod
    def advance_stage(
        cls,
        db: Session,
        application_id: int,
        reason: str,
        actor_user: User
    ) -> ApplicationWorkflowRouting:
        """
        Advances application to the next configured statutory stage.
        Mandates recorded reason and verifies permissions.
        """
        routing = db.query(ApplicationWorkflowRouting).filter(
            ApplicationWorkflowRouting.application_id == application_id
        ).first()
        if not routing:
            raise ValueError(f"Routing record not found for application {application_id}")

        sequence = ROUTE_STAGE_SEQUENCES.get(routing.route_type, ROUTE_STAGE_SEQUENCES[ApplicationRouteType.ONLY_SCRUTINY.value])
        try:
            curr_index = sequence.index(routing.current_stage)
        except ValueError:
            curr_index = 0

        if curr_index >= len(sequence) - 1:
            raise ValueError(f"Application is already at final stage ({routing.current_stage}).")

        prev_stage = routing.current_stage
        next_stage = sequence[curr_index + 1]
        next_eligible = sequence[curr_index + 2] if curr_index + 2 < len(sequence) else None

        now = datetime.utcnow()
        routing.current_stage = next_stage
        routing.stage_entry_at = now
        routing.next_eligible_stage = next_eligible
        routing.updated_at = now

        if next_stage == WorkflowStage.CLOSED.value or next_stage == WorkflowStage.FINAL_APPROVAL.value:
            routing.processing_status = "STAGE_COMPLETED"
            if next_stage == WorkflowStage.CLOSED.value:
                routing.is_completed = True

        # Complete previous obligation if exists
        prev_obligations = db.query(Obligation).filter(
            Obligation.application_id == application_id,
            Obligation.status == "RUNNING"
        ).all()
        for obl in prev_obligations:
            ClockEngine.complete_obligation(
                db=db,
                obligation_id=obl.id,
                reason=f"Stage {prev_stage} completed. Advanced to {next_stage}.",
                actor=actor_user.email
            )

        # Spawn next obligation if applicable
        if next_stage == WorkflowStage.EVC_STAGE.value:
            create_obligation(
                db=db,
                institution_id=routing.application.institution_id,
                application_id=application_id,
                obligation_type=ObligationType.EVC_SCHEDULING.value,
                title=f"EVC Inspection Scheduling: {routing.application.reference_no}",
                description="Expert Visit Committee panel appointment, conflict check, and physical visit scheduling.",
                responsible_entity="Regional Inspection Bureau",
                responsible_role=ResponsibleRole.AICTE_OFFICER.value,
                responsible_post="Regional Officer",
                source_event="STAGE_ADVANCEMENT_TO_EVC",
                aph_clause="APH 2024-27 Clause 2.5",
                configured_days=20,
                actor_user=actor_user
            )
        elif next_stage == WorkflowStage.SAC_SHC_STAGE.value:
            create_obligation(
                db=db,
                institution_id=routing.application.institution_id,
                application_id=application_id,
                obligation_type=ObligationType.SAC_SHC_REVIEW.value,
                title=f"SAC/SHC Hearing: {routing.application.reference_no}",
                description="Standing Appeal Committee statutory hearing and compliance verification.",
                responsible_entity="Standing Appeal Committee",
                responsible_role=ResponsibleRole.SAC_SHC_COMMITTEE.value,
                responsible_post="SAC Committee Chairman",
                source_event="STAGE_ADVANCEMENT_TO_SAC",
                aph_clause="APH 2024-27 Clause 2.8",
                configured_days=10,
                actor_user=actor_user
            )

        # Log Stage Movement History
        history = StageMovementHistory(
            application_id=application_id,
            routing_id=routing.id,
            from_stage=prev_stage,
            to_stage=next_stage,
            action="ADVANCE",
            reason=reason,
            officer_id=actor_user.id,
            created_at=now
        )
        db.add(history)

        # Notify institution
        app_obj = routing.application
        notif = Notification(
            user_id=app_obj.submitting_user_id or 1,
            application_id=application_id,
            title=f"Application Stage Update: {next_stage}",
            message=f"Your application {app_obj.reference_no} has progressed from {prev_stage} to {next_stage}. Action/Reason: {reason}",
            notification_type="INFO"
        )
        db.add(notif)

        db.commit()
        db.refresh(routing)
        return routing

    @classmethod
    def return_to_institution(
        cls,
        db: Session,
        application_id: int,
        reason: str,
        actor_user: User,
        clarification_days: int = 7
    ) -> ApplicationWorkflowRouting:
        """
        Returns application to institution for deficiency rectification.
        Pauses AICTE scrutiny clock and starts institution clarification clock (Phase 4).
        """
        routing = db.query(ApplicationWorkflowRouting).filter(
            ApplicationWorkflowRouting.application_id == application_id
        ).first()
        if not routing:
            raise ValueError(f"Routing not found for application {application_id}")

        now = datetime.utcnow()
        prev_stage = routing.current_stage
        routing.processing_status = "AWAITING_CLARIFICATION"
        routing.updated_at = now

        # Update application status
        app_obj = routing.application
        app_obj.status = ApplicationStatus.CLARIFICATION_REQUESTED

        # Pause any running AICTE obligation
        running_obls = db.query(Obligation).filter(
            Obligation.application_id == application_id,
            Obligation.status == "RUNNING"
        ).all()
        for obl in running_obls:
            ClockEngine.pause_obligation_clock(
                db=db,
                obligation_id=obl.id,
                reason=f"Application returned to institution for clarification: {reason}",
                actor=actor_user.email,
                pause_state="PAUSED_INSTITUTION"
            )

        # Create Institution Clarification Obligation in Promise Ledger
        create_obligation(
            db=db,
            institution_id=app_obj.institution_id,
            application_id=application_id,
            obligation_type=ObligationType.INSTITUTION_CLARIFICATION.value,
            title=f"Clarification Response: {app_obj.reference_no}",
            description=f"Submit requested documents/clarifications within statutory timeline. Deficiencies: {reason}",
            responsible_entity=app_obj.institution.name,
            responsible_role=ResponsibleRole.INSTITUTION.value,
            responsible_post="Head of Institution / Principal",
            source_event="CLARIFICATION_REQUESTED",
            aph_clause="APH 2024-27 Clause 2.4",
            configured_days=clarification_days,
            deadline_type="CALENDAR_DAYS",
            actor_user=actor_user
        )

        # Stage movement history
        history = StageMovementHistory(
            application_id=application_id,
            routing_id=routing.id,
            from_stage=prev_stage,
            to_stage=WorkflowStage.RE_SCRUTINY.value,
            action="RETURN_FOR_CLARIFICATION",
            reason=reason,
            officer_id=actor_user.id,
            created_at=now
        )
        db.add(history)

        # Notify institution
        notif = Notification(
            user_id=app_obj.submitting_user_id or 1,
            application_id=application_id,
            title="Action Required: Clarification Requested",
            message=f"Application {app_obj.reference_no} returned for corrections. Deadline: {clarification_days} days. Reason: {reason}",
            notification_type="WARNING"
        )
        db.add(notif)

        db.commit()
        db.refresh(routing)
        return routing

    @classmethod
    def resume_after_institution_resubmission(
        cls,
        db: Session,
        application_id: int,
        reason: str,
        actor_user: User
    ) -> ApplicationWorkflowRouting:
        """
        When institution submits corrections, resumes AICTE processing clock and shifts to RE_SCRUTINY.
        """
        routing = db.query(ApplicationWorkflowRouting).filter(
            ApplicationWorkflowRouting.application_id == application_id
        ).first()
        if not routing:
            raise ValueError(f"Routing not found for application {application_id}")

        now = datetime.utcnow()
        routing.current_stage = WorkflowStage.RE_SCRUTINY.value
        routing.processing_status = "IN_PROGRESS"
        routing.updated_at = now

        app_obj = routing.application
        app_obj.status = ApplicationStatus.CORRECTION_SUBMITTED

        # Mark institution clarification obligation as MET
        clarification_obls = db.query(Obligation).filter(
            Obligation.application_id == application_id,
            Obligation.obligation_type == ObligationType.INSTITUTION_CLARIFICATION.value,
            Obligation.status == "RUNNING"
        ).all()
        for obl in clarification_obls:
            ClockEngine.complete_obligation(
                db=db,
                obligation_id=obl.id,
                reason="Institution submitted correction/clarification.",
                actor=actor_user.email
            )

        # Resume paused AICTE scrutiny clocks
        paused_obls = db.query(Obligation).filter(
            Obligation.application_id == application_id,
            Obligation.clock_state == "PAUSED_INSTITUTION"
        ).all()
        for obl in paused_obls:
            ClockEngine.resume_obligation_clock(
                db=db,
                obligation_id=obl.id,
                reason="Institution submitted clarifications; AICTE scrutiny clock resumed.",
                actor=actor_user.email
            )

        # Record Stage History
        history = StageMovementHistory(
            application_id=application_id,
            routing_id=routing.id,
            from_stage=WorkflowStage.SCRUTINY_STAGE.value,
            to_stage=WorkflowStage.RE_SCRUTINY.value,
            action="RE_SCRUTINY",
            reason=reason,
            officer_id=actor_user.id,
            created_at=now
        )
        db.add(history)

        db.commit()
        db.refresh(routing)
        return routing
