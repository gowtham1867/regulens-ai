from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.undertaking import TimeBoundUndertaking, UndertakingStatus
from app.models.obligation import Obligation, ObligationType, ResponsibleRole
from app.models.application import Application
from app.models.user import User
from app.services.obligation_service import create_obligation
from app.services.clock_engine import ClockEngine
from app.services.audit_service import record_audit_event


def generate_undertaking_number(db: Session) -> str:
    count = db.query(TimeBoundUndertaking).count() + 1
    year = datetime.utcnow().year
    return f"UT-{year}-{count:04d}"


class UndertakingService:
    @classmethod
    def create_undertaking(
        cls,
        db: Session,
        application_id: int,
        condition_title: str,
        condition_description: str,
        statutory_deadline_months: int = 6,
        aph_clause: str = "APH 2024-27 Clause 7.12",
        actor_user: Optional[User] = None
    ) -> TimeBoundUndertaking:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found.")

        now = datetime.utcnow()
        due_date = now + timedelta(days=statutory_deadline_months * 30)
        ut_no = generate_undertaking_number(db)

        # Create obligation in Promise Ledger
        obl = create_obligation(
            db=db,
            institution_id=app.institution_id,
            application_id=app.id,
            obligation_type=ObligationType.TIME_BOUND_UNDERTAKING.value,
            title=f"Statutory Undertaking: {condition_title}",
            description=condition_description,
            responsible_entity=app.institution.name,
            responsible_role=ResponsibleRole.INSTITUTION.value,
            responsible_post="Head of Institution / Principal",
            source_event="CONDITIONAL_APPROVAL_GRANTED",
            aph_clause=aph_clause,
            configured_days=statutory_deadline_months * 30,
            deadline_type="CALENDAR_DAYS",
            actor_user=actor_user
        )

        undertaking = TimeBoundUndertaking(
            undertaking_no=ut_no,
            application_id=app.id,
            institution_id=app.institution_id,
            obligation_id=obl.id,
            condition_title=condition_title,
            condition_description=condition_description,
            aph_clause=aph_clause,
            statutory_deadline_months=statutory_deadline_months,
            due_date=due_date,
            status=UndertakingStatus.PENDING.value
        )
        db.add(undertaking)
        db.commit()
        db.refresh(undertaking)

        record_audit_event(
            db=db,
            action="UNDERTAKING_CREATED",
            entity_type="UNDERTAKING",
            entity_id=str(undertaking.id),
            actor=actor_user,
            details=f"Created statutory undertaking {undertaking.undertaking_no}: {condition_title}"
        )

        return undertaking

    @classmethod
    def submit_compliance_evidence(
        cls,
        db: Session,
        undertaking_id: int,
        evidence_description: str,
        document_id: Optional[int],
        institution_user: User
    ) -> TimeBoundUndertaking:
        ut = db.query(TimeBoundUndertaking).filter(TimeBoundUndertaking.id == undertaking_id).first()
        if not ut:
            raise ValueError(f"Undertaking {undertaking_id} not found.")

        now = datetime.utcnow()
        ut.status = UndertakingStatus.EVIDENCE_SUBMITTED.value
        ut.evidence_submission_date = now
        ut.evidence_description = evidence_description
        ut.evidence_document_id = document_id
        ut.updated_at = now

        db.commit()
        db.refresh(ut)
        return ut

    @classmethod
    def review_compliance(
        cls,
        db: Session,
        undertaking_id: int,
        is_compliant: bool,
        review_notes: str,
        officer_user: User
    ) -> TimeBoundUndertaking:
        ut = db.query(TimeBoundUndertaking).filter(TimeBoundUndertaking.id == undertaking_id).first()
        if not ut:
            raise ValueError(f"Undertaking {undertaking_id} not found.")

        now = datetime.utcnow()
        ut.status = UndertakingStatus.COMPLIANT.value if is_compliant else UndertakingStatus.DEFICIENT.value
        ut.officer_review_notes = review_notes
        ut.reviewed_by_officer_id = officer_user.id
        ut.reviewed_at = now
        ut.updated_at = now

        # Update obligation status in Promise Ledger
        if ut.obligation_id:
            if is_compliant:
                ClockEngine.complete_obligation(
                    db=db,
                    obligation_id=ut.obligation_id,
                    reason=f"Officer verified undertaking compliance: {review_notes}",
                    actor=officer_user.email
                )

        db.commit()
        db.refresh(ut)
        return ut
