from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.obligation import Obligation, ObligationEventHistory, ClockInterval
from app.models.application import Application
from app.models.workflow_routing import ApplicationWorkflowRouting, StageMovementHistory
from app.models.document_validity import DocumentValidityRecord
from app.models.undertaking import TimeBoundUndertaking
from app.models.audit import AuditEvent
from app.services.clock_engine import ClockEngine
from app.services.audit_service import verify_audit_chain_integrity


class ExplanationService:
    """
    Deterministic explainability service providing comprehensive mathematical and regulatory
    breakdowns for deadlines, routing choices, obligations, and escalations.
    Complies with Phase 5 specifications.
    """

    @classmethod
    def explain_obligation(cls, db: Session, obligation_id: int) -> Dict[str, Any]:
        obligation = db.query(Obligation).filter(Obligation.id == obligation_id).first()
        if not obligation:
            raise ValueError(f"Obligation {obligation_id} not found.")

        # Re-compute clock breakdown
        clock_calc = ClockEngine.compute_obligation_due_date(
            start_dt=obligation.start_date,
            configured_days=obligation.configured_days,
            deadline_type=obligation.deadline_type,
            region="ALL",
            paused_days=obligation.total_paused_days,
            extension_days=obligation.approved_extension_days,
            db=db
        )

        # Audit Chain Verification for this entity
        audit_records = db.query(AuditEvent).filter(
            AuditEvent.entity_type == "OBLIGATION",
            AuditEvent.entity_id == str(obligation.id)
        ).all()
        chain_status = verify_audit_chain_integrity(db)

        # History timeline
        events = db.query(ObligationEventHistory).filter(
            ObligationEventHistory.obligation_id == obligation.id
        ).order_by(ObligationEventHistory.id.asc()).all()

        timeline = []
        for ev in events:
            timeline.append({
                "timestamp": ev.created_at.isoformat(),
                "event_type": ev.event_type,
                "actor": ev.triggered_by,
                "reason": ev.reason,
                "previous_state": ev.previous_state,
                "new_state": ev.new_state
            })

        # Clock intervals breakdown
        intervals = db.query(ClockInterval).filter(
            ClockInterval.obligation_id == obligation.id
        ).all()
        interval_data = [
            {
                "clock_state": inv.clock_state,
                "started_at": inv.started_at.isoformat(),
                "ended_at": inv.ended_at.isoformat() if inv.ended_at else "ACTIVE",
                "duration_seconds": inv.duration_seconds,
                "reason": inv.reason,
                "actor": inv.actor
            }
            for inv in intervals
        ]

        # Template-based deterministic summary
        summary_sentence = (
            f"Deadline calculated using {obligation.configured_days} configured {obligation.deadline_type.lower().replace('_', ' ')}. "
            f"{obligation.excluded_holidays_count} statutory holidays/weekends were excluded. "
            f"The clock was paused for {obligation.total_paused_days} day(s) during clarifications. "
            f"{obligation.approved_extension_days} approved extension days were recorded. "
            f"Current effective due date: {obligation.due_date.strftime('%d-%b-%Y %H:%M UTC')}."
        )

        return {
            "entity_type": "OBLIGATION",
            "entity_id": obligation.id,
            "obligation_no": obligation.obligation_no,
            "title": obligation.title,
            "obligation_type": obligation.obligation_type,
            "summary_explanation": summary_sentence,
            # Regulatory Origin
            "source_event": obligation.source_event,
            "regulatory_rule": {
                "aph_edition": "AICTE Approval Process Handbook (APH) 2024-2027",
                "aph_clause": obligation.aph_clause,
                "is_aph_verified": obligation.is_aph_verified,
                "authority_type": "Statutory AICTE Handbook Regulation" if obligation.is_aph_verified else "Administrator Configured Operational Parameter"
            },
            # Deadline Mathematics
            "deadline_calculation": {
                "start_date": obligation.start_date.isoformat(),
                "deadline_type": obligation.deadline_type,
                "configured_days": obligation.configured_days,
                "excluded_holidays_count": obligation.excluded_holidays_count,
                "excluded_holidays_details": clock_calc["excluded_holidays"][:10],
                "total_paused_days": obligation.total_paused_days,
                "approved_extension_days": obligation.approved_extension_days,
                "base_due_date": clock_calc["base_due_date"],
                "effective_due_date": obligation.due_date.isoformat(),
                "days_remaining": clock_calc["days_remaining"],
                "is_overdue": clock_calc["is_overdue"]
            },
            # Responsibility & Clock State
            "responsibility": {
                "responsible_entity": obligation.responsible_entity,
                "responsible_role": obligation.responsible_role,
                "responsible_post": obligation.responsible_post,
                "current_status": obligation.status,
                "clock_state": obligation.clock_state,
                "escalation_level": obligation.escalation_level
            },
            # Event History & Intervals
            "timeline": timeline,
            "clock_intervals": interval_data,
            # Cryptographic Verification
            "audit_verification": {
                "audit_records_count": len(audit_records),
                "chain_integrity_valid": chain_status["valid"],
                "chain_status": chain_status["status"],
                "verified_at": chain_status.get("verified_at", datetime.utcnow().isoformat())
            }
        }

    @classmethod
    def explain_application_routing(cls, db: Session, application_id: int) -> Dict[str, Any]:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found.")

        routing = db.query(ApplicationWorkflowRouting).filter(
            ApplicationWorkflowRouting.application_id == application_id
        ).first()

        history = db.query(StageMovementHistory).filter(
            StageMovementHistory.application_id == application_id
        ).order_by(StageMovementHistory.id.asc()).all()

        stage_history = [
            {
                "from_stage": h.from_stage,
                "to_stage": h.to_stage,
                "action": h.action,
                "reason": h.reason,
                "timestamp": h.created_at.isoformat(),
                "officer": h.officer.name if h.officer else "System Automation"
            }
            for h in history
        ]

        chain_status = verify_audit_chain_integrity(db)

        return {
            "entity_type": "APPLICATION_ROUTING",
            "application_id": app.id,
            "reference_no": app.reference_no,
            "category": app.category.value if hasattr(app.category, "value") else str(app.category),
            "assigned_route": routing.route_type if routing else "ONLY_SCRUTINY",
            "current_stage": routing.current_stage if routing else "SCRUTINY_STAGE",
            "next_eligible_stage": routing.next_eligible_stage if routing else None,
            "routing_reason": routing.routing_reason if routing else "Standard Extension of Approval",
            "regulatory_rule": {
                "aph_edition": "AICTE Approval Process Handbook (APH) 2024-2027",
                "aph_clause": "APH 2024-27 Chapter I & II (Approval Routing Matrices)",
                "is_aph_verified": True
            },
            "stage_history": stage_history,
            "audit_verification": {
                "chain_integrity_valid": chain_status["valid"],
                "chain_status": chain_status["status"]
            }
        }

    @classmethod
    def explain_document_validity(cls, db: Session, record_id: int) -> Dict[str, Any]:
        record = db.query(DocumentValidityRecord).filter(DocumentValidityRecord.id == record_id).first()
        if not record:
            raise ValueError(f"Document validity record {record_id} not found.")

        now = datetime.utcnow()
        days_remaining = (record.expiry_date - now).days

        return {
            "entity_type": "DOCUMENT_VALIDITY",
            "record_id": record.id,
            "document_type": record.document_type,
            "document_name": record.document_name,
            "issuing_authority": record.issuing_authority,
            "expiry_date": record.expiry_date.isoformat(),
            "days_remaining": days_remaining,
            "status": record.status,
            "summary_explanation": (
                f"{record.document_type} issued by {record.issuing_authority} expires on {record.expiry_date.strftime('%d-%b-%Y')}. "
                f"Statutory compliance under APH 2024-27 Clause 4.1 mandates an active valid deed/NOC throughout academic approval."
            ),
            "regulatory_rule": {
                "aph_edition": "AICTE Approval Process Handbook (APH) 2024-2027",
                "aph_clause": "APH 2024-27 Clause 4.1 (Mandatory Statutory Certificates)",
                "is_aph_verified": True
            }
        }
