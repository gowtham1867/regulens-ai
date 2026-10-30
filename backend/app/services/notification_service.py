from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.models.institution import InstitutionMembership
from app.models.application import Application
from app.models.obligation import Obligation, ObligationStatus, ObligationEventHistory, ClockState
from app.services.audit_service import record_audit_event


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "INFO",
    link: Optional[str] = None,
    application_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    action_type: Optional[str] = None,
    details: Optional[str] = None
) -> Notification:
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
        application_id=application_id,
        institution_id=institution_id,
        action_type=action_type,
        details=details,
        is_read=False
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def notify_institution_users(
    db: Session,
    institution_id: int,
    title: str,
    message: str,
    notification_type: str = "INFO",
    link: Optional[str] = None,
    application_id: Optional[int] = None,
    action_type: Optional[str] = None,
    details: Optional[str] = None
) -> List[Notification]:
    """
    Deliver targeted, confidential notifications strictly to users affiliated
    with the given institution. Never leaks to other institutions or third parties.
    """
    memberships = db.query(InstitutionMembership).filter(
        InstitutionMembership.institution_id == institution_id
    ).all()
    user_ids = {m.user_id for m in memberships}

    # Also include the submitting user if known
    if application_id:
        app = db.query(Application).filter(Application.id == application_id).first()
        if app and app.submitting_user_id:
            user_ids.add(app.submitting_user_id)

    created = []
    for uid in user_ids:
        user = db.query(User).filter(User.id == uid, User.is_active == True).first()
        if user:
            notif = create_notification(
                db=db,
                user_id=uid,
                title=title,
                message=message,
                notification_type=notification_type,
                link=link,
                application_id=application_id,
                institution_id=institution_id,
                action_type=action_type,
                details=details
            )
            created.append(notif)
    return created


def notify_all_officers(
    db: Session,
    title: str,
    message: str,
    notification_type: str = "INFO",
    link: Optional[str] = None,
    application_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    action_type: Optional[str] = None,
    details: Optional[str] = None
) -> List[Notification]:
    officers = db.query(User).filter(
        User.role.in_([UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]),
        User.is_active == True
    ).all()
    created = []
    for officer in officers:
        notif = create_notification(
            db=db,
            user_id=officer.id,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link,
            application_id=application_id,
            institution_id=institution_id,
            action_type=action_type,
            details=details
        )
        created.append(notif)
    return created


def dispatch_obligation_escalation(
    db: Session,
    obligation_id: int,
    new_escalation_level: int,
    reason: str
) -> List[Notification]:
    """
    Hierarchical Alert & Escalation Engine (Phase 10):
    Dispatches alerts with idempotency check against duplicate alerts.
    Level 1: 7-day reminder
    Level 2: 3-day urgent warning
    Level 3: Overdue breach notice & Bureau escalation
    """
    obl = db.query(Obligation).filter(Obligation.id == obligation_id).first()
    if not obl:
        return []

    # Idempotency check: Don't repeat identical escalation level
    if obl.escalation_level >= new_escalation_level and obl.status == ObligationStatus.RUNNING.value:
        return []

    now = datetime.utcnow()
    obl.escalation_level = new_escalation_level
    if new_escalation_level >= 3:
        obl.status = ObligationStatus.OVERDUE.value
        obl.clock_state = ClockState.BREACHED.value
    obl.updated_at = now

    # Record Event History
    ev = ObligationEventHistory(
        obligation_id=obl.id,
        event_type="ESCALATION_TRIGGERED" if new_escalation_level >= 3 else "REMINDER_SENT",
        triggered_by="AUTOMATED_ESCALATION_ENGINE",
        reason=f"Escalation Level {new_escalation_level}: {reason}",
        previous_state=f"Level {obl.escalation_level - 1}",
        new_state=f"Level {new_escalation_level}",
        created_at=now
    )
    db.add(ev)

    notifications_sent = []
    notif_type = "WARNING" if new_escalation_level < 3 else "CRITICAL"

    # Alert Institution if obligation belongs to institution
    if obl.responsible_role == "INSTITUTION":
        inst_notifs = notify_institution_users(
            db=db,
            institution_id=obl.institution_id,
            title=f"Statutory Notice (Level {new_escalation_level}): {obl.title}",
            message=f"{reason}. Applicable clause: {obl.aph_clause}. Due: {obl.due_date.strftime('%d-%b-%Y')}",
            notification_type=notif_type,
            application_id=obl.application_id,
            action_type="OBLIGATION_DEADLINE",
            details=f"Obligation: {obl.obligation_no}"
        )
        notifications_sent.extend(inst_notifs)

    # For Level 2 & 3: Alert Officers & Regional Directorate
    if new_escalation_level >= 2:
        officer_notifs = notify_all_officers(
            db=db,
            title=f"PENDENCY ESCALATION [L{new_escalation_level}]: {obl.title}",
            message=f"{obl.responsible_entity} has pending obligation {obl.obligation_no}. Status: {reason}",
            notification_type=notif_type,
            application_id=obl.application_id,
            institution_id=obl.institution_id,
            action_type="OFFICER_ESCALATION"
        )
        notifications_sent.extend(officer_notifs)

    db.commit()
    return notifications_sent


def run_automated_escalation_scan(db: Session) -> Dict[str, Any]:
    """
    Automated job that evaluates all active obligations against statutory escalation thresholds.
    """
    now = datetime.utcnow()
    active_obls = db.query(Obligation).filter(
        Obligation.status.in_([ObligationStatus.RUNNING.value, ObligationStatus.PENDING.value, ObligationStatus.OVERDUE.value])
    ).all()

    escalated_count = 0
    reminded_count = 0

    for obl in active_obls:
        # If paused, do not escalate clock
        if obl.clock_state.startswith("PAUSED"):
            continue

        days_remaining = (obl.due_date - now).days

        if days_remaining < 0 and obl.escalation_level < 3:
            dispatch_obligation_escalation(
                db=db,
                obligation_id=obl.id,
                new_escalation_level=3,
                reason=f"Deadline breached by {abs(days_remaining)} days without authorized extension."
            )
            escalated_count += 1
        elif 0 <= days_remaining <= 3 and obl.escalation_level < 2:
            dispatch_obligation_escalation(
                db=db,
                obligation_id=obl.id,
                new_escalation_level=2,
                reason=f"Urgent: {days_remaining} days remaining until statutory deadline."
            )
            reminded_count += 1
        elif 3 < days_remaining <= 7 and obl.escalation_level < 1:
            dispatch_obligation_escalation(
                db=db,
                obligation_id=obl.id,
                new_escalation_level=1,
                reason=f"Reminder: {days_remaining} days remaining until deadline."
            )
            reminded_count += 1

    return {
        "timestamp": now.isoformat(),
        "total_active_evaluated": len(active_obls),
        "escalated_count": escalated_count,
        "reminded_count": reminded_count
    }
