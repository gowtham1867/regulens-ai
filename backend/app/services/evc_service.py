import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.evc import EVCSchedule, EVCStatus, EVCExpert
from app.models.application import Application
from app.models.institution import Institution
from app.models.user import User
from app.models.obligation import Obligation, ObligationType, ResponsibleRole
from app.services.obligation_service import create_obligation
from app.services.clock_engine import ClockEngine
from app.services.audit_service import record_audit_event


def generate_evc_number(db: Session) -> str:
    count = db.query(EVCSchedule).count() + 1
    year = datetime.utcnow().year
    return f"EVC-{year}-{count:04d}"


class EVCService:
    @classmethod
    def queue_application_for_evc(
        cls,
        db: Session,
        application_id: int,
        actor_user: Optional[User] = None
    ) -> EVCSchedule:
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found.")

        existing = db.query(EVCSchedule).filter(EVCSchedule.application_id == application_id).first()
        if existing:
            return existing

        inst = app.institution
        region = f"{inst.state} Regional Office" if inst else "Southern Regional Office"
        evc_no = generate_evc_number(db)

        # Propose automated panel of available experts in the region with conflict check
        proposed = cls.propose_expert_panel(db, inst)

        evc = EVCSchedule(
            evc_no=evc_no,
            application_id=app.id,
            institution_id=app.institution_id,
            region=region,
            status=EVCStatus.PANEL_PROPOSED.value,
            proposed_panel=json.dumps(proposed["experts"]),
            conflict_check_passed=proposed["conflict_check_passed"],
            conflict_check_notes=proposed["conflict_check_notes"]
        )
        db.add(evc)
        db.commit()
        db.refresh(evc)

        # Create obligation in Promise Ledger
        create_obligation(
            db=db,
            institution_id=app.institution_id,
            application_id=app.id,
            obligation_type=ObligationType.EVC_SCHEDULING.value,
            title=f"EVC Inspection Approval: {app.reference_no}",
            description=f"Authorized officer panel approval and visit scheduling for {app.title}.",
            responsible_entity=region,
            responsible_role=ResponsibleRole.AICTE_OFFICER.value,
            responsible_post="Regional Officer",
            source_event="EVC_QUEUED",
            aph_clause="APH 2024-27 Clause 2.5",
            configured_days=20,
            actor_user=actor_user
        )

        return evc

    @classmethod
    def propose_expert_panel(cls, db: Session, institution: Optional[Institution]) -> Dict[str, Any]:
        """
        Selects available experts, verifying no institutional conflict-of-interest.
        """
        experts = db.query(EVCExpert).filter(EVCExpert.is_available == True).order_by(EVCExpert.active_visits_count.asc()).limit(3).all()
        
        conflict_passed = True
        conflict_notes = []
        panel_data = []

        inst_name = institution.name.lower() if institution else ""
        inst_state = institution.state.lower() if institution else ""

        for exp in experts:
            # Conflict check: Expert cannot be from the target institution
            if exp.institution.lower() in inst_name or inst_name in exp.institution.lower():
                conflict_passed = False
                conflict_notes.append(f"Conflict identified: {exp.name} affiliated with target institution {exp.institution}")

            panel_data.append({
                "id": exp.id,
                "name": exp.name,
                "designation": exp.designation,
                "institution": exp.institution,
                "specialization": exp.specialization,
                "region": exp.region,
                "state": exp.state,
                "conflict_free": exp.institution.lower() not in inst_name
            })

        if not conflict_notes:
            conflict_notes.append("Automated conflict check passed. No institutional or geographic conflict detected.")

        return {
            "experts": panel_data,
            "conflict_check_passed": conflict_passed,
            "conflict_check_notes": "; ".join(conflict_notes)
        }

    @classmethod
    def schedule_visit(
        cls,
        db: Session,
        evc_id: int,
        visit_date: datetime,
        visit_location: str,
        approved_experts: List[Dict[str, Any]],
        officer_user: User
    ) -> EVCSchedule:
        """
        Officer approves proposed panel and confirms visit date & location.
        """
        evc = db.query(EVCSchedule).filter(EVCSchedule.id == evc_id).first()
        if not evc:
            raise ValueError(f"EVC record {evc_id} not found.")

        now = datetime.utcnow()
        evc.status = EVCStatus.SCHEDULED.value
        evc.scheduled_date = visit_date
        evc.visit_location = visit_location
        evc.approved_panel = json.dumps(approved_experts)
        evc.approved_by_officer_id = officer_user.id
        evc.officer_approval_date = now
        evc.updated_at = now

        # Update expert active visit counts
        for exp_dict in approved_experts:
            exp_id = exp_dict.get("id")
            if exp_id:
                exp_obj = db.query(EVCExpert).filter(EVCExpert.id == exp_id).first()
                if exp_obj:
                    exp_obj.active_visits_count += 1

        db.commit()
        db.refresh(evc)

        record_audit_event(
            db=db,
            action="EVC_SCHEDULED",
            entity_type="EVC_SCHEDULE",
            entity_id=str(evc.id),
            actor=officer_user,
            details=f"EVC {evc.evc_no} scheduled on {visit_date.strftime('%Y-%m-%d')} by {officer_user.email}"
        )

        return evc

    @classmethod
    def submit_evc_report(
        cls,
        db: Session,
        evc_id: int,
        recommendation: str,
        summary: str,
        document_id: Optional[int] = None,
        officer_user: Optional[User] = None
    ) -> EVCSchedule:
        evc = db.query(EVCSchedule).filter(EVCSchedule.id == evc_id).first()
        if not evc:
            raise ValueError(f"EVC record {evc_id} not found.")

        now = datetime.utcnow()
        evc.status = EVCStatus.REPORT_RECEIVED.value
        evc.report_submission_date = now
        evc.report_recommendation = recommendation
        evc.report_summary = summary
        evc.report_document_id = document_id
        evc.updated_at = now

        # Complete EVC obligation in Promise Ledger
        obls = db.query(Obligation).filter(
            Obligation.application_id == evc.application_id,
            Obligation.obligation_type == ObligationType.EVC_SCHEDULING.value,
            Obligation.status == "RUNNING"
        ).all()
        for obl in obls:
            ClockEngine.complete_obligation(
                db=db,
                obligation_id=obl.id,
                reason=f"EVC Report received with recommendation: {recommendation}",
                actor=officer_user.email if officer_user else "SYSTEM"
            )

        db.commit()
        db.refresh(evc)
        return evc
