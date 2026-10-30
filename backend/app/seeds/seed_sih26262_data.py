import os
import json
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal, Base, engine
from app.models.user import User, UserRole
from app.models.institution import Institution
from app.models.application import Application, ApplicationCategory, ApplicationStatus
from app.models.obligation import (
    Obligation, ObligationType, ObligationStatus, ClockState,
    ResponsibleRole, ObligationEventHistory, ClockInterval
)
from app.models.workflow_routing import (
    ApplicationWorkflowRouting, ApplicationRouteType, WorkflowStage, StageMovementHistory
)
from app.models.evc import EVCSchedule, EVCStatus, EVCExpert
from app.models.undertaking import TimeBoundUndertaking, UndertakingStatus
from app.models.document_validity import DocumentValidityRecord, DocumentValidityStatus
from app.models.admin_config import HolidayCalendar, WorkflowRouteTemplate
from app.models.scheduler_job import SchedulerJob
from app.services.scheduler import init_default_scheduler_jobs


def seed_sih26262():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        print("[PS 26262 Seed] Starting enhanced regulatory data initialization...")

        # ---------------------------------------------------------------------
        # 1. Holiday Calendars (Statutory Non-Working Days)
        # ---------------------------------------------------------------------
        holidays_data = [
            ("ALL", datetime(2025, 1, 26), "Republic Day"),
            ("ALL", datetime(2025, 3, 14), "Holi"),
            ("ALL", datetime(2025, 3, 31), "Id-ul-Fitr"),
            ("ALL", datetime(2025, 4, 18), "Good Friday"),
            ("ALL", datetime(2025, 8, 15), "Independence Day"),
            ("ALL", datetime(2025, 10, 2), "Mahatma Gandhi Jayanti"),
            ("ALL", datetime(2025, 10, 20), "Diwali (Deepavali)"),
            ("ALL", datetime(2025, 12, 25), "Christmas Day"),
            ("SOUTHERN", datetime(2025, 1, 14), "Pongal / Makar Sankranti"),
            ("NORTHERN", datetime(2025, 4, 13), "Baisakhi"),
            ("WESTERN", datetime(2025, 8, 27), "Ganesh Chaturthi"),
        ]
        for reg, dt, name in holidays_data:
            existing = db.query(HolidayCalendar).filter(
                HolidayCalendar.date == dt,
                HolidayCalendar.name == name
            ).first()
            if not existing:
                db.add(HolidayCalendar(region=reg, date=dt, name=name, is_statutory=True))

        # ---------------------------------------------------------------------
        # 2. Workflow Route Templates
        # ---------------------------------------------------------------------
        route_templates = [
            (
                ApplicationCategory.NEW_INSTITUTION.value,
                ApplicationRouteType.FULL_SCRUTINY_EVC_SAC.value,
                ["SCRUTINY_STAGE", "EVC_STAGE", "SAC_SHC_STAGE", "FINAL_APPROVAL", "CLOSED"],
                15, 20, 10, 7
            ),
            (
                ApplicationCategory.INCREASE_IN_INTAKE.value,
                ApplicationRouteType.SCRUTINY_EVC.value,
                ["SCRUTINY_STAGE", "EVC_STAGE", "FINAL_APPROVAL", "CLOSED"],
                15, 15, 10, 7
            ),
            (
                ApplicationCategory.CHANGE_OF_SITE.value,
                ApplicationRouteType.SCRUTINY_EVC.value,
                ["SCRUTINY_STAGE", "EVC_STAGE", "FINAL_APPROVAL", "CLOSED"],
                15, 20, 10, 7
            ),
            (
                ApplicationCategory.INTRODUCTION_OF_NEW_COURSE.value,
                ApplicationRouteType.ONLY_SCRUTINY.value,
                ["SCRUTINY_STAGE", "FINAL_APPROVAL", "CLOSED"],
                15, 0, 0, 7
            ),
            (
                ApplicationCategory.EXTENSION_OF_APPROVAL.value,
                ApplicationRouteType.ONLY_SCRUTINY.value,
                ["SCRUTINY_STAGE", "FINAL_APPROVAL", "CLOSED"],
                15, 0, 0, 7
            ),
        ]
        for cat, rtype, stages, scr, evc, sac, clar in route_templates:
            existing = db.query(WorkflowRouteTemplate).filter(WorkflowRouteTemplate.category == cat).first()
            if not existing:
                db.add(WorkflowRouteTemplate(
                    category=cat,
                    route_type=rtype,
                    stages_json=json.dumps(stages),
                    default_scrutiny_days=scr,
                    default_evc_days=evc,
                    default_sac_shc_days=sac,
                    default_institution_clarification_days=clar,
                    deadline_type="WORKING_DAYS"
                ))

        # ---------------------------------------------------------------------
        # 3. EVC Expert Panel Registry
        # ---------------------------------------------------------------------
        experts_data = [
            ("Prof. Dr. Rajeshwari Sundaram", "Senior Professor & Head", "IIT Madras", "Computer Science & Engineering", "Southern", "Tamil Nadu"),
            ("Dr. Anand V. Kulkarni", "Dean of Academic Infrastructure", "NIT Karnataka, Surathkal", "Civil & Structural Engineering", "Southern", "Karnataka"),
            ("Dr. Meenakshi Sharma", "Professor of Electrical Engineering", "Delhi Technological University (DTU)", "Electrical & Power Systems", "Northern", "Delhi"),
            ("Prof. Suresh Chandra Rao", "Director", "College of Engineering, Pune (COEP)", "Mechanical & Industrial Engineering", "Western", "Maharashtra"),
            ("Dr. Preeti Ganguly", "Professor & AICTE Nominee", "Jadavpur University", "Chemical & Environmental Engineering", "Eastern", "West Bengal"),
            ("Dr. K. S. Balasubramanian", "Former Dean", "Anna University, Chennai", "Architecture & Planning", "Southern", "Tamil Nadu"),
            ("Dr. Nitin Deshmukh", "AICTE Regional Inspection Chair", "VNIT Nagpur", "Electronics & Communication", "Western", "Maharashtra"),
            ("Dr. Harish Verma", "Professor", "IIT Roorkee", "Safety & Fire Protection", "Northern", "Uttarakhand"),
        ]
        for name, desig, inst_name, spec, reg, st in experts_data:
            existing = db.query(EVCExpert).filter(EVCExpert.name == name).first()
            if not existing:
                db.add(EVCExpert(
                    name=name,
                    designation=desig,
                    institution=inst_name,
                    specialization=spec,
                    region=reg,
                    state=st,
                    active_visits_count=0,
                    is_available=True
                ))

        db.commit()

        # ---------------------------------------------------------------------
        # 4. Populate Application Workflow Routings & Promise Ledger Obligations
        # ---------------------------------------------------------------------
        apps = db.query(Application).all()
        now = datetime.utcnow()
        officers = db.query(User).filter(User.role == UserRole.AICTE_OFFICER).all()
        officer = officers[0] if officers else None

        print(f"[PS 26262 Seed] Routing {len(apps)} existing applications...")

        for idx, app in enumerate(apps):
            inst = app.institution
            cat = app.category

            # Determine route and stage for realistic demonstration
            if cat == ApplicationCategory.NEW_INSTITUTION:
                route_type = ApplicationRouteType.FULL_SCRUTINY_EVC_SAC.value
                current_stage = WorkflowStage.EVC_STAGE.value if idx % 2 == 0 else WorkflowStage.SCRUTINY_STAGE.value
                status = "IN_PROGRESS"
                reason = "APH 2024-27 Chapter I: New Institution establishment mandates Scrutiny, EVC, and SAC review."
            elif cat in [ApplicationCategory.CHANGE_OF_SITE, ApplicationCategory.INCREASE_IN_INTAKE]:
                route_type = ApplicationRouteType.SCRUTINY_EVC.value
                current_stage = WorkflowStage.EVC_STAGE.value if idx % 2 == 0 else WorkflowStage.SCRUTINY_STAGE.value
                status = "IN_PROGRESS"
                reason = "APH 2024-27 Chapter II: Infrastructure changes mandate Scrutiny and physical EVC inspection."
            elif app.status == ApplicationStatus.CLARIFICATION_REQUESTED:
                route_type = ApplicationRouteType.ONLY_SCRUTINY.value
                current_stage = WorkflowStage.RE_SCRUTINY.value
                status = "AWAITING_CLARIFICATION"
                reason = "APH 2024-27 Clause 2.4: Clarification requested on land title deed; processing paused."
            elif app.status == ApplicationStatus.APPROVED:
                route_type = ApplicationRouteType.ONLY_SCRUTINY.value
                current_stage = WorkflowStage.FINAL_APPROVAL.value
                status = "STAGE_COMPLETED"
                reason = "Standard Extension of Approval completed."
            else:
                route_type = ApplicationRouteType.ONLY_SCRUTINY.value
                current_stage = WorkflowStage.SCRUTINY_STAGE.value
                status = "IN_PROGRESS"
                reason = "Standard Extension of Approval (EoA) scrutiny."

            existing_routing = db.query(ApplicationWorkflowRouting).filter(
                ApplicationWorkflowRouting.application_id == app.id
            ).first()

            if not existing_routing:
                routing = ApplicationWorkflowRouting(
                    application_id=app.id,
                    route_type=route_type,
                    current_stage=current_stage,
                    stage_entry_at=now - timedelta(days=idx * 2 + 1),
                    stage_deadline=now + timedelta(days=15 - idx),
                    assigned_officer_id=officer.id if officer else None,
                    assigned_committee="Scrutiny Committee (Regional)",
                    processing_status=status,
                    is_completed=(current_stage == WorkflowStage.FINAL_APPROVAL.value),
                    routing_reason=reason
                )
                db.add(routing)
                db.flush()

                # Add stage history
                db.add(StageMovementHistory(
                    application_id=app.id,
                    routing_id=routing.id,
                    from_stage=None,
                    to_stage=current_stage,
                    action="ADVANCE" if current_stage != WorkflowStage.SCRUTINY_STAGE.value else "INITIALIZE",
                    reason=f"Application routed to {current_stage}. {reason}",
                    officer_id=officer.id if officer else None,
                    created_at=now - timedelta(days=idx * 2 + 1)
                ))

            # Seed Obligations in Promise Ledger
            existing_obls = db.query(Obligation).filter(Obligation.application_id == app.id).first()
            if not existing_obls:
                # 1. Scrutiny Obligation
                # Variety in due dates: some overdue, some approaching, some paused
                if idx == 0:
                    # Urgent: Due in 2 days (Today's 10 candidate)
                    due_dt = now + timedelta(days=2, hours=4)
                    obl_status = ObligationStatus.RUNNING.value
                    c_state = ClockState.RUNNING.value
                    esc_lvl = 2
                    paused_days = 0
                elif idx == 1:
                    # Overdue by 4 days (Escalation level 3)
                    due_dt = now - timedelta(days=4)
                    obl_status = ObligationStatus.OVERDUE.value
                    c_state = ClockState.BREACHED.value
                    esc_lvl = 3
                    paused_days = 0
                elif idx == 2:
                    # Paused awaiting institution response
                    due_dt = now + timedelta(days=10)
                    obl_status = ObligationStatus.RUNNING.value
                    c_state = ClockState.PAUSED_INSTITUTION.value
                    esc_lvl = 0
                    paused_days = 5
                elif app.status == ApplicationStatus.APPROVED:
                    due_dt = now - timedelta(days=10)
                    obl_status = ObligationStatus.MET.value
                    c_state = ClockState.STOPPED_MET.value
                    esc_lvl = 0
                    paused_days = 0
                else:
                    due_dt = now + timedelta(days=7 + idx)
                    obl_status = ObligationStatus.RUNNING.value
                    c_state = ClockState.RUNNING.value
                    esc_lvl = 0
                    paused_days = 0

                obl_no = f"OBL-2025-{1000 + idx:04d}"
                obl = Obligation(
                    obligation_no=obl_no,
                    institution_id=app.institution_id,
                    application_id=app.id,
                    obligation_type=ObligationType.APPLICATION_SCRUTINY.value,
                    title=f"Application Scrutiny: {app.reference_no}",
                    description=f"Statutory scrutiny review for {app.title} under {route_type} route.",
                    responsible_entity=f"Scrutiny Cell ({inst.state if inst else 'Regional'})",
                    responsible_role=ResponsibleRole.AICTE_OFFICER.value,
                    responsible_post="Scrutiny Officer",
                    source_event="APPLICATION_SUBMISSION",
                    aph_clause="APH 2024-27 Clause 2.3",
                    is_aph_verified=True,
                    deadline_type="WORKING_DAYS",
                    configured_days=15,
                    creation_date=now - timedelta(days=15),
                    start_date=now - timedelta(days=15),
                    due_date=due_dt,
                    original_due_date=due_dt - timedelta(days=paused_days),
                    status=obl_status,
                    clock_state=c_state,
                    total_paused_days=paused_days,
                    approved_extension_days=0,
                    excluded_holidays_count=4,
                    escalation_level=esc_lvl,
                    completion_date=now if obl_status == ObligationStatus.MET.value else None,
                    verification_status="VERIFIED" if obl_status == ObligationStatus.MET.value else "UNVERIFIED"
                )
                db.add(obl)
                db.flush()

                # Event History
                db.add(ObligationEventHistory(
                    obligation_id=obl.id,
                    event_type="CREATED",
                    triggered_by="SYSTEM_AUTOMATION",
                    reason=f"Statutory scrutiny obligation registered on application submission.",
                    previous_state=None,
                    new_state=obl_status,
                    created_at=now - timedelta(days=15)
                ))

                if paused_days > 0:
                    # Record pause interval
                    db.add(ClockInterval(
                        obligation_id=obl.id,
                        clock_state=ClockState.PAUSED_INSTITUTION.value,
                        started_at=now - timedelta(days=paused_days),
                        ended_at=None,
                        reason="Paused awaiting institution clarification submission.",
                        actor=officer.email if officer else "SYSTEM"
                    ))
                    db.add(ObligationEventHistory(
                        obligation_id=obl.id,
                        event_type="CLOCK_PAUSED",
                        triggered_by=officer.email if officer else "SYSTEM",
                        reason="Application returned to institution for clarification.",
                        previous_state=ClockState.RUNNING.value,
                        new_state=ClockState.PAUSED_INSTITUTION.value,
                        created_at=now - timedelta(days=paused_days)
                    ))

                # 2. For Applications in EVC Stage: Seed EVCSchedule
                if current_stage == WorkflowStage.EVC_STAGE.value:
                    evc_experts = db.query(EVCExpert).limit(3).all()
                    exp_panel = [
                        {"id": e.id, "name": e.name, "designation": e.designation, "institution": e.institution, "specialization": e.specialization}
                        for e in evc_experts
                    ]
                    evc = EVCSchedule(
                        evc_no=f"EVC-2025-{100 + idx:04d}",
                        application_id=app.id,
                        institution_id=app.institution_id,
                        region=f"{inst.state if inst else 'Southern'} Regional Office",
                        status=EVCStatus.PANEL_PROPOSED.value if idx % 2 == 0 else EVCStatus.SCHEDULED.value,
                        scheduled_date=now + timedelta(days=5 + idx) if idx % 2 != 0 else None,
                        visit_location=inst.address if inst else "Campus Premises",
                        proposed_panel=json.dumps(exp_panel),
                        approved_panel=json.dumps(exp_panel) if idx % 2 != 0 else None,
                        conflict_check_passed=True,
                        conflict_check_notes="Automated conflict check passed. No expert belongs to target institution.",
                        approved_by_officer_id=officer.id if (officer and idx % 2 != 0) else None,
                        officer_approval_date=now - timedelta(days=1) if idx % 2 != 0 else None
                    )
                    db.add(evc)

        db.commit()

        # ---------------------------------------------------------------------
        # 5. Seed Time-Bound Undertakings
        # ---------------------------------------------------------------------
        institutions = db.query(Institution).all()
        for idx, inst in enumerate(institutions):
            app = inst.applications[0] if inst.applications else None
            if not app:
                continue

            existing_ut = db.query(TimeBoundUndertaking).filter(TimeBoundUndertaking.institution_id == inst.id).first()
            if not existing_ut:
                ut = TimeBoundUndertaking(
                    undertaking_no=f"UT-2025-{100 + idx:04d}",
                    application_id=app.id,
                    institution_id=inst.id,
                    condition_title=f"Completion of Additional Laboratory Block (Floor 2)" if idx % 2 == 0 else "Recruitment of Cadre Ratio Faculty in CSE",
                    condition_description="Statutory condition specified in conditional approval letter. Full compliance report with photographic and geo-tagged proof required within 6 months.",
                    aph_clause="APH 2024-27 Clause 7.12",
                    statutory_deadline_months=6,
                    due_date=now + timedelta(days=60 - idx * 10),
                    status=UndertakingStatus.PENDING.value if idx % 2 == 0 else UndertakingStatus.EVIDENCE_SUBMITTED.value,
                    evidence_submission_date=now - timedelta(days=2) if idx % 2 != 0 else None,
                    evidence_description="Uploaded completion certificate from Chartered Architect with geo-tagged images." if idx % 2 != 0 else None
                )
                db.add(ut)

        # ---------------------------------------------------------------------
        # 6. Seed Document Validity Records (Lease Deeds, Fire Safety NOC)
        # ---------------------------------------------------------------------
        for idx, inst in enumerate(institutions):
            # Fire Safety NOC
            existing_fire = db.query(DocumentValidityRecord).filter(
                DocumentValidityRecord.institution_id == inst.id,
                DocumentValidityRecord.document_type == "FIRE_SAFETY_NOC"
            ).first()
            if not existing_fire:
                # 1 institution expiring soon (18 days remaining), 1 expired, others valid
                if idx == 0:
                    exp_dt = now + timedelta(days=18)
                    v_status = DocumentValidityStatus.EXPIRING_SOON.value
                elif idx == 1:
                    exp_dt = now - timedelta(days=10)
                    v_status = DocumentValidityStatus.EXPIRED.value
                else:
                    exp_dt = now + timedelta(days=280)
                    v_status = DocumentValidityStatus.VALID.value

                db.add(DocumentValidityRecord(
                    institution_id=inst.id,
                    document_type="FIRE_SAFETY_NOC",
                    document_name="Fire Safety Certificate / NOC",
                    issuing_authority="State Directorate of Fire & Rescue Services",
                    issue_date=now - timedelta(days=340),
                    expiry_date=exp_dt,
                    validity_years=1.0,
                    status=v_status,
                    days_remaining=(exp_dt - now).days,
                    ocr_extracted=True,
                    notes="Verified via Issuer Registry API."
                ))

            # Land Lease Deed
            existing_lease = db.query(DocumentValidityRecord).filter(
                DocumentValidityRecord.institution_id == inst.id,
                DocumentValidityRecord.document_type == "LEASE_DEED"
            ).first()
            if not existing_lease:
                lease_exp = now + timedelta(days=365 * 28)  # 28 years remaining
                db.add(DocumentValidityRecord(
                    institution_id=inst.id,
                    document_type="LEASE_DEED",
                    document_name="Registered Land Lease Deed (30 Years)",
                    issuing_authority="Sub-Registrar Office",
                    issue_date=now - timedelta(days=365 * 2),
                    expiry_date=lease_exp,
                    validity_years=30.0,
                    status=DocumentValidityStatus.VALID.value,
                    days_remaining=(lease_exp - now).days,
                    ocr_extracted=True,
                    notes="Statutory requirement: Minimum 30 years lease period satisfied."
                ))

        # ---------------------------------------------------------------------
        # 7. Initialize Scheduler Jobs
        # ---------------------------------------------------------------------
        init_default_scheduler_jobs(db)

        db.commit()
        print("[PS 26262 Seed] Enhanced regulatory data seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"[PS 26262 Seed] Error: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_sih26262()
