from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.models.institution import InstitutionMembership
from app.models.application import Application


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
        # Check active user
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


