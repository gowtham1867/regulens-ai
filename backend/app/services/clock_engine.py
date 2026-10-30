from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.obligation import (
    Obligation,
    ObligationStatus,
    ClockState,
    ObligationEventHistory,
    ClockInterval,
)
from app.models.admin_config import HolidayCalendar
from app.models.audit import AuditEvent


# Standard AICTE & National Gazetted Holidays (Fallback / Baseline)
STANDARD_GAZETTED_HOLIDAYS_2025_2026 = [
    (date(2025, 1, 26), "Republic Day"),
    (date(2025, 3, 14), "Holi"),
    (date(2025, 3, 31), "Id-ul-Fitr"),
    (date(2025, 4, 18), "Good Friday"),
    (date(2025, 5, 12), "Buddha Purnima"),
    (date(2025, 6, 7), "Id-ul-Zuha (Bakrid)"),
    (date(2025, 7, 6), "Muharram"),
    (date(2025, 8, 15), "Independence Day"),
    (date(2025, 9, 5), "Milad-un-Nabi"),
    (date(2025, 10, 2), "Mahatma Gandhi's Birthday"),
    (date(2025, 10, 2), "Dussehra"),
    (date(2025, 10, 20), "Diwali (Deepavali)"),
    (date(2025, 11, 5), "Guru Nanak's Birthday"),
    (date(2025, 12, 25), "Christmas Day"),
    # 2026
    (date(2026, 1, 26), "Republic Day"),
    (date(2026, 3, 4), "Holi"),
    (date(2026, 3, 20), "Id-ul-Fitr"),
    (date(2026, 4, 3), "Good Friday"),
    (date(2026, 8, 15), "Independence Day"),
    (date(2026, 10, 2), "Mahatma Gandhi's Birthday"),
    (date(2026, 11, 8), "Diwali"),
    (date(2026, 12, 25), "Christmas Day"),
]


class ClockEngine:
    """
    Deterministic, explainable regulatory clock engine for AICTE obligations and deadlines.
    Complies with Phase 4 specifications.
    """

    @staticmethod
    def is_holiday(check_date: date, region: str = "ALL", state: Optional[str] = None, db: Optional[Session] = None) -> Tuple[bool, Optional[str]]:
        """
        Check if a given calendar day is a statutory non-working holiday.
        Returns (is_holiday, holiday_name).
        """
        # Saturday (5) or Sunday (6)
        if check_date.weekday() >= 5:
            return True, "Weekend (Saturday/Sunday)"

        # Check DB Holiday Calendar if session provided
        if db is not None:
            db_holiday = db.query(HolidayCalendar).filter(
                HolidayCalendar.date == datetime(check_date.year, check_date.month, check_date.day),
                HolidayCalendar.region.in_(["ALL", region, f"STATE_{state}" if state else "ALL"])
            ).first()
            if db_holiday:
                return True, db_holiday.name

        # Check standard gazetted list
        for h_date, h_name in STANDARD_GAZETTED_HOLIDAYS_2025_2026:
            if h_date == check_date:
                return True, h_name

        return False, None

    @classmethod
    def calculate_working_days_deadline(
        cls,
        start_dt: datetime,
        working_days: int,
        region: str = "ALL",
        state: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Tuple[datetime, int, List[Dict[str, str]]]:
        """
        Step through days sequentially, excluding weekends and statutory holidays.
        Returns: (calculated_due_date, total_excluded_days, list_of_excluded_details)
        """
        current_date = start_dt.date()
        added_days = 0
        excluded_days_count = 0
        excluded_details = []

        while added_days < working_days:
            current_date += timedelta(days=1)
            is_hol, reason = cls.is_holiday(current_date, region=region, state=state, db=db)
            if is_hol:
                excluded_days_count += 1
                excluded_details.append({
                    "date": current_date.isoformat(),
                    "reason": reason or "Holiday"
                })
            else:
                added_days += 1

        due_datetime = datetime(
            current_date.year, current_date.month, current_date.day,
            hour=start_dt.hour, minute=start_dt.minute, second=start_dt.second
        )
        return due_datetime, excluded_days_count, excluded_details

    @classmethod
    def compute_obligation_due_date(
        cls,
        start_dt: datetime,
        configured_days: int,
        deadline_type: str = "WORKING_DAYS",
        region: str = "ALL",
        state: Optional[str] = None,
        paused_days: int = 0,
        extension_days: int = 0,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Full mathematical calculation of deadline with complete explainability breakdown.
        """
        if deadline_type == "WORKING_DAYS":
            base_due, excluded_count, excluded_list = cls.calculate_working_days_deadline(
                start_dt, configured_days, region=region, state=state, db=db
            )
        else:
            base_due = start_dt + timedelta(days=configured_days)
            excluded_count = 0
            excluded_list = []

        total_adjustments = paused_days + extension_days
        effective_due_date = base_due + timedelta(days=total_adjustments)

        now = datetime.utcnow()
        time_diff = effective_due_date - now
        days_remaining = time_diff.days
        seconds_remaining = int(time_diff.total_seconds())
        is_overdue = seconds_remaining < 0

        return {
            "start_date": start_dt.isoformat(),
            "configured_days": configured_days,
            "deadline_type": deadline_type,
            "base_due_date": base_due.isoformat(),
            "excluded_holidays_count": excluded_count,
            "excluded_holidays": excluded_list,
            "total_paused_days": paused_days,
            "approved_extension_days": extension_days,
            "effective_due_date": effective_due_date.isoformat(),
            "days_remaining": days_remaining,
            "seconds_remaining": seconds_remaining,
            "is_overdue": is_overdue
        }

    @classmethod
    def pause_obligation_clock(
        cls,
        db: Session,
        obligation_id: int,
        reason: str,
        actor: str = "SYSTEM",
        pause_state: str = ClockState.PAUSED_INSTITUTION.value
    ) -> Obligation:
        """
        Pauses the processing clock. Creates an active ClockInterval and records audit event.
        """
        obligation = db.query(Obligation).filter(Obligation.id == obligation_id).first()
        if not obligation:
            raise ValueError(f"Obligation with ID {obligation_id} not found.")

        if obligation.clock_state.startswith("PAUSED"):
            return obligation  # Already paused

        previous_state = obligation.clock_state
        obligation.clock_state = pause_state
        obligation.updated_at = datetime.utcnow()

        # Create active clock interval
        interval = ClockInterval(
            obligation_id=obligation.id,
            clock_state=pause_state,
            started_at=datetime.utcnow(),
            reason=reason,
            actor=actor
        )
        db.add(interval)

        # Record event history
        event = ObligationEventHistory(
            obligation_id=obligation.id,
            event_type="CLOCK_PAUSED",
            triggered_by=actor,
            reason=reason,
            previous_state=previous_state,
            new_state=pause_state,
            created_at=datetime.utcnow()
        )
        db.add(event)
        db.commit()
        db.refresh(obligation)
        return obligation

    @classmethod
    def resume_obligation_clock(
        cls,
        db: Session,
        obligation_id: int,
        reason: str,
        actor: str = "SYSTEM"
    ) -> Obligation:
        """
        Resumes the clock. Closes active interval, calculates paused days, extends due_date.
        """
        obligation = db.query(Obligation).filter(Obligation.id == obligation_id).first()
        if not obligation:
            raise ValueError(f"Obligation with ID {obligation_id} not found.")

        if not obligation.clock_state.startswith("PAUSED"):
            return obligation  # Not paused

        now = datetime.utcnow()
        previous_state = obligation.clock_state

        # Find latest open clock interval
        open_interval = db.query(ClockInterval).filter(
            ClockInterval.obligation_id == obligation.id,
            ClockInterval.ended_at == None
        ).order_by(desc(ClockInterval.id)).first()

        paused_days_added = 0
        if open_interval:
            open_interval.ended_at = now
            duration = int((now - open_interval.started_at).total_seconds())
            open_interval.duration_seconds = duration
            # Round up to days for calendar extension
            paused_days_added = max(1, int((now - open_interval.started_at).days) or 1)

        obligation.total_paused_days += paused_days_added
        obligation.due_date = obligation.due_date + timedelta(days=paused_days_added)
        obligation.clock_state = ClockState.RUNNING.value
        obligation.updated_at = now

        event = ObligationEventHistory(
            obligation_id=obligation.id,
            event_type="CLOCK_RESUMED",
            triggered_by=actor,
            reason=f"{reason} (Paused for {paused_days_added} days; due date extended accordingly)",
            previous_state=previous_state,
            new_state=ClockState.RUNNING.value,
            clock_interval_days=paused_days_added,
            created_at=now
        )
        db.add(event)
        db.commit()
        db.refresh(obligation)
        return obligation

    @classmethod
    def grant_extension(
        cls,
        db: Session,
        obligation_id: int,
        additional_days: int,
        reason: str,
        approved_by: str = "Regional Officer"
    ) -> Obligation:
        """
        Records an approved statutory extension and recalculates the due date.
        """
        obligation = db.query(Obligation).filter(Obligation.id == obligation_id).first()
        if not obligation:
            raise ValueError(f"Obligation with ID {obligation_id} not found.")

        now = datetime.utcnow()
        previous_due = obligation.due_date
        obligation.approved_extension_days += additional_days
        obligation.due_date = obligation.due_date + timedelta(days=additional_days)
        obligation.updated_at = now

        event = ObligationEventHistory(
            obligation_id=obligation.id,
            event_type="EXTENSION_APPROVED",
            triggered_by=approved_by,
            reason=f"Approved statutory extension of {additional_days} days. Reason: {reason}",
            previous_state=previous_due.isoformat(),
            new_state=obligation.due_date.isoformat(),
            clock_interval_days=additional_days,
            created_at=now
        )
        db.add(event)
        db.commit()
        db.refresh(obligation)
        return obligation

    @classmethod
    def complete_obligation(
        cls,
        db: Session,
        obligation_id: int,
        reason: str,
        actor: str = "SYSTEM",
        evidence_refs: Optional[str] = None
    ) -> Obligation:
        """
        Marks an obligation as completed/MET and stops the clock.
        """
        obligation = db.query(Obligation).filter(Obligation.id == obligation_id).first()
        if not obligation:
            raise ValueError(f"Obligation with ID {obligation_id} not found.")

        now = datetime.utcnow()
        previous_status = obligation.status
        obligation.status = ObligationStatus.MET.value
        obligation.clock_state = ClockState.STOPPED_MET.value
        obligation.completion_date = now
        obligation.verification_status = "VERIFIED"
        if evidence_refs:
            obligation.evidence_refs = evidence_refs
        obligation.updated_at = now

        # Close any open intervals
        open_interval = db.query(ClockInterval).filter(
            ClockInterval.obligation_id == obligation.id,
            ClockInterval.ended_at == None
        ).first()
        if open_interval:
            open_interval.ended_at = now
            open_interval.duration_seconds = int((now - open_interval.started_at).total_seconds())

        event = ObligationEventHistory(
            obligation_id=obligation.id,
            event_type="COMPLETED",
            triggered_by=actor,
            reason=reason,
            previous_state=previous_status,
            new_state=ObligationStatus.MET.value,
            created_at=now
        )
        db.add(event)
        db.commit()
        db.refresh(obligation)
        return obligation
