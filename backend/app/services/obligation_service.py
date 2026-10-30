import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, and_

from app.models.obligation import (
    Obligation,
    ObligationType,
    ObligationStatus,
    ClockState,
    ResponsibleRole,
    ObligationEventHistory,
    ClockInterval,
)
from app.models.institution import Institution
from app.models.application import Application
from app.models.user import User
from app.services.clock_engine import ClockEngine
from app.services.audit_service import record_audit_event


def generate_obligation_number(db: Session) -> str:
    current_year = datetime.utcnow().year
    count = db.query(Obligation).count() + 1
    return f"OBL-{current_year}-{count:04d}"


def create_obligation(
    db: Session,
    institution_id: int,
    obligation_type: str,
    title: str,
    description: str,
    responsible_entity: str,
    responsible_role: str,
    responsible_post: str,
    source_event: str,
    aph_clause: str = "APH 2024-27 Clause 2.3",
    is_aph_verified: bool = True,
    deadline_type: str = "WORKING_DAYS",
    configured_days: int = 30,
    application_id: Optional[int] = None,
    source_rule_id: Optional[int] = None,
    evidence_refs: Optional[str] = None,
    notes: Optional[str] = None,
    actor_user: Optional[User] = None
) -> Obligation:
    """
    Creates an obligation in the central Promise Ledger with deterministic clock calculation.
    """
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    state = institution.state if institution else None

    start_dt = datetime.utcnow()
    clock_calc = ClockEngine.compute_obligation_due_date(
        start_dt=start_dt,
        configured_days=configured_days,
        deadline_type=deadline_type,
        region="ALL",
        state=state,
        db=db
    )

    due_dt = datetime.fromisoformat(clock_calc["effective_due_date"])
    obl_no = generate_obligation_number(db)

    obligation = Obligation(
        obligation_no=obl_no,
        institution_id=institution_id,
        application_id=application_id,
        obligation_type=obligation_type,
        title=title,
        description=description,
        responsible_entity=responsible_entity,
        responsible_role=responsible_role,
        responsible_post=responsible_post,
        source_event=source_event,
        source_rule_id=source_rule_id,
        aph_clause=aph_clause,
        is_aph_verified=is_aph_verified,
        deadline_type=deadline_type,
        configured_days=configured_days,
        creation_date=start_dt,
        start_date=start_dt,
        due_date=due_dt,
        original_due_date=due_dt,
        status=ObligationStatus.RUNNING.value,
        clock_state=ClockState.RUNNING.value,
        total_paused_days=0,
        approved_extension_days=0,
        excluded_holidays_count=clock_calc["excluded_holidays_count"],
        evidence_refs=evidence_refs,
        notes=notes
    )
    db.add(obligation)
    db.flush()

    # Initial event history
    initial_event = ObligationEventHistory(
        obligation_id=obligation.id,
        event_type="CREATED",
        triggered_by=actor_user.email if actor_user else "SYSTEM",
        reason=f"Obligation registered under {source_event}. Statutory deadline calculated: {configured_days} {deadline_type.lower()}.",
        previous_state=None,
        new_state=ObligationStatus.RUNNING.value,
        clock_interval_days=configured_days,
        created_at=start_dt
    )
    db.add(initial_event)
    db.commit()
    db.refresh(obligation)

    # Cryptographic Audit Log
    record_audit_event(
        db=db,
        action="OBLIGATION_CREATED",
        entity_type="OBLIGATION",
        entity_id=str(obligation.id),
        actor=actor_user,
        details=f"Created obligation {obligation.obligation_no} for institution {institution_id}: {title}"
    )

    return obligation


def get_obligations_for_institution(db: Session, institution_id: int) -> List[Obligation]:
    return db.query(Obligation).filter(Obligation.institution_id == institution_id).order_by(Obligation.due_date.asc()).all()


def get_obligations_for_application(db: Session, application_id: int) -> List[Obligation]:
    return db.query(Obligation).filter(Obligation.application_id == application_id).order_by(Obligation.due_date.asc()).all()


def get_officer_inbox_obligations(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Officer Daily Inbox — Today's 10 (Phase 6.C):
    Returns prioritized list of obligations with transparent priority factors.
    Priority formula:
    1. Overdue cases (Highest priority)
    2. Approaching deadlines (< 3 days, < 7 days)
    3. Escalated obligations (escalation_level > 0)
    4. Time-bound undertakings nearing statutory expiry
    """
    now = datetime.utcnow()
    active_obligations = db.query(Obligation).filter(
        Obligation.status.in_([ObligationStatus.RUNNING.value, ObligationStatus.PENDING.value, ObligationStatus.OVERDUE.value, ObligationStatus.BREACHED.value])
    ).all()

    ranked_items = []
    for obl in active_obligations:
        days_remaining = (obl.due_date - now).days
        is_overdue = days_remaining < 0

        # Transparent Priority Scoring
        priority_score = 0
        urgency_reasons = []

        if is_overdue:
            priority_score += 1000 + abs(days_remaining) * 10
            urgency_reasons.append(f"Statutory deadline breached by {abs(days_remaining)} days")
        elif days_remaining <= 3:
            priority_score += 500 + (3 - days_remaining) * 50
            urgency_reasons.append(f"Critical statutory deadline approaching in {days_remaining} day(s)")
        elif days_remaining <= 7:
            priority_score += 200 + (7 - days_remaining) * 20
            urgency_reasons.append(f"Action required within {days_remaining} days")
        else:
            priority_score += max(0, 100 - days_remaining)

        if obl.escalation_level > 0:
            priority_score += obl.escalation_level * 150
            urgency_reasons.append(f"Escalation Level {obl.escalation_level} active")

        if obl.clock_state == ClockState.PAUSED_INSTITUTION.value:
            urgency_reasons.append("Paused: Awaiting institution response/clarification")

        # Application details if available
        app_ref = None
        app_title = None
        if obl.application_id:
            app = db.query(Application).filter(Application.id == obl.application_id).first()
            if app:
                app_ref = app.reference_no
                app_title = app.title

        ranked_items.append({
            "obligation_id": obl.id,
            "obligation_no": obl.obligation_no,
            "institution_id": obl.institution_id,
            "institution_name": obl.institution.name if obl.institution else "Unknown",
            "application_id": obl.application_id,
            "application_reference": app_ref,
            "application_title": app_title,
            "obligation_type": obl.obligation_type,
            "title": obl.title,
            "description": obl.description,
            "responsible_entity": obl.responsible_entity,
            "responsible_role": obl.responsible_role,
            "responsible_post": obl.responsible_post,
            "aph_clause": obl.aph_clause,
            "due_date": obl.due_date.isoformat(),
            "days_remaining": days_remaining,
            "is_overdue": is_overdue,
            "status": obl.status,
            "clock_state": obl.clock_state,
            "escalation_level": obl.escalation_level,
            "priority_score": priority_score,
            "urgency_reasons": urgency_reasons,
            "next_required_action": get_next_action_recommendation(obl)
        })

    # Sort descending by priority_score
    ranked_items.sort(key=lambda x: x["priority_score"], reverse=True)
    return ranked_items[:limit]


def get_next_action_recommendation(obl: Obligation) -> str:
    if obl.status == ObligationStatus.OVERDUE.value:
        return f"Issue immediate statutory breach notice or summon competent committee under {obl.aph_clause}"
    if obl.clock_state == ClockState.PAUSED_INSTITUTION.value:
        return "Review pending correction submissions from institution"
    if obl.obligation_type == ObligationType.APPLICATION_SCRUTINY.value:
        return "Complete deficiency validation and proceed to scrutiny sign-off"
    if obl.obligation_type == ObligationType.EVC_SCHEDULING.value:
        return "Approve proposed expert inspection panel"
    if obl.obligation_type == ObligationType.EVC_COMPLETION.value:
        return "Upload/review Expert Visit Committee inspection report"
    if obl.obligation_type == ObligationType.SAC_SHC_REVIEW.value:
        return "Conduct Standing Appeal Committee hearing"
    if obl.obligation_type == ObligationType.TIME_BOUND_UNDERTAKING.value:
        return "Verify submitted compliance affidavit and photographic evidence"
    return "Complete pending statutory review"
