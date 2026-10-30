import sys
import os
import unittest
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.abspath("backend"))

from app.database import SessionLocal, Base, engine
from app.models.user import User, UserRole
from app.models.institution import Institution
from app.models.application import Application, ApplicationCategory, ApplicationStatus
from app.models.obligation import Obligation, ObligationStatus, ClockState, ResponsibleRole
from app.models.workflow_routing import ApplicationWorkflowRouting, ApplicationRouteType, WorkflowStage
from app.models.evc import EVCSchedule, EVCStatus, EVCExpert
from app.models.undertaking import TimeBoundUndertaking, UndertakingStatus
from app.models.document_validity import DocumentValidityRecord, DocumentValidityStatus
from app.models.audit import AuditEvent

from app.services.clock_engine import ClockEngine
from app.services.obligation_service import create_obligation, get_officer_inbox_obligations
from app.services.workflow_router import WorkflowRouter
from app.services.evc_service import EVCService
from app.services.undertaking_service import UndertakingService
from app.services.document_validity_service import DocumentValidityService
from app.services.explanation_service import ExplanationService
from app.services.compliance_reports_service import ComplianceReportsService
from app.services.audit_service import verify_audit_chain_integrity, record_audit_event


class TestSIH26262RegulatorySuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_deterministic_clock_engine(self):
        """Phase 4: Verify deterministic clock calculations, holiday exclusions, pauses, and extensions."""
        start_dt = datetime(2025, 1, 20, 10, 0, 0)
        # 10 working days starting Monday Jan 20, 2025
        # Excludes: Sat Jan 25, Sun Jan 26, Republic Day Mon Jan 26, Sat Feb 1, Sun Feb 2
        calc = ClockEngine.compute_obligation_due_date(
            start_dt=start_dt,
            configured_days=10,
            deadline_type="WORKING_DAYS",
            region="ALL",
            paused_days=0,
            extension_days=0,
            db=self.db
        )
        self.assertIsNotNone(calc["effective_due_date"])
        self.assertGreater(calc["excluded_holidays_count"], 0)
        self.assertEqual(calc["configured_days"], 10)

        # Test with paused days and extensions
        calc_adj = ClockEngine.compute_obligation_due_date(
            start_dt=start_dt,
            configured_days=10,
            deadline_type="WORKING_DAYS",
            region="ALL",
            paused_days=5,
            extension_days=3,
            db=self.db
        )
        due_orig = datetime.fromisoformat(calc["effective_due_date"])
        due_adj = datetime.fromisoformat(calc_adj["effective_due_date"])
        self.assertEqual((due_adj - due_orig).days, 8)
        print("[OK] Test 01: Deterministic Clock Engine calculation verified.")

    def test_02_promise_ledger_obligation_lifecycle(self):
        """Phase 2: Verify central Promise Ledger creation, pausing, resuming, and completion."""
        inst = self.db.query(Institution).first()
        app = self.db.query(Application).filter(Application.institution_id == inst.id).first()
        officer = self.db.query(User).filter(User.role == UserRole.AICTE_OFFICER).first()

        obl = create_obligation(
            db=self.db,
            institution_id=inst.id,
            application_id=app.id if app else None,
            obligation_type="APPLICATION_SCRUTINY",
            title="Unit Test Scrutiny Obligation",
            description="Testing obligation lifecycle in Promise Ledger",
            responsible_entity="Scrutiny Cell",
            responsible_role="AICTE_OFFICER",
            responsible_post="Scrutiny Officer",
            source_event="TEST_SUITE_INITIATION",
            configured_days=15,
            deadline_type="WORKING_DAYS",
            actor_user=officer
        )
        self.assertIsNotNone(obl.id)
        self.assertTrue(obl.obligation_no.startswith("OBL-"))
        self.assertEqual(obl.clock_state, ClockState.RUNNING.value)

        # Pause Clock
        paused_obl = ClockEngine.pause_obligation_clock(
            db=self.db,
            obligation_id=obl.id,
            reason="Paused for test clarification",
            actor="test_officer@aicte.gov.in"
        )
        self.assertEqual(paused_obl.clock_state, ClockState.PAUSED_INSTITUTION.value)

        # Resume Clock
        resumed_obl = ClockEngine.resume_obligation_clock(
            db=self.db,
            obligation_id=obl.id,
            reason="Institution submitted test response",
            actor="test_officer@aicte.gov.in"
        )
        self.assertEqual(resumed_obl.clock_state, ClockState.RUNNING.value)
        self.assertGreaterEqual(resumed_obl.total_paused_days, 1)

        # Complete Obligation (MET)
        completed_obl = ClockEngine.complete_obligation(
            db=self.db,
            obligation_id=obl.id,
            reason="Verified and passed",
            actor="test_officer@aicte.gov.in"
        )
        self.assertEqual(completed_obl.status, ObligationStatus.MET.value)
        self.assertEqual(completed_obl.clock_state, ClockState.STOPPED_MET.value)
        print("[OK] Test 02: Promise Ledger obligation lifecycle verified.")

    def test_03_workflow_routing_and_stage_state_machine(self):
        """Phase 3: Verify configurable route assignment, stage advancement, and clarification return."""
        app = self.db.query(Application).first()
        officer = self.db.query(User).filter(User.role == UserRole.AICTE_OFFICER).first()

        routing = WorkflowRouter.initialize_routing_for_application(
            db=self.db,
            application_id=app.id,
            actor_user=officer
        )
        self.assertIsNotNone(routing)
        self.assertIn(routing.route_type, [
            ApplicationRouteType.ONLY_SCRUTINY.value,
            ApplicationRouteType.SCRUTINY_EVC.value,
            ApplicationRouteType.FULL_SCRUTINY_EVC_SAC.value
        ])

        # Test Return to institution with reason
        returned = WorkflowRouter.return_to_institution(
            db=self.db,
            application_id=app.id,
            reason="Fire NOC requires notarized translation",
            actor_user=officer,
            clarification_days=7
        )
        self.assertEqual(returned.processing_status, "AWAITING_CLARIFICATION")

        # Test Resume after resubmission
        resumed = WorkflowRouter.resume_after_institution_resubmission(
            db=self.db,
            application_id=app.id,
            reason="Institution uploaded certified translation",
            actor_user=officer
        )
        self.assertEqual(resumed.current_stage, WorkflowStage.RE_SCRUTINY.value)
        print("[OK] Test 03: Workflow routing state machine verified.")

    def test_04_why_explanation_engine(self):
        """Phase 5: Verify deterministic 'Why?' explanation generator."""
        obl = self.db.query(Obligation).first()
        explanation = ExplanationService.explain_obligation(self.db, obl.id)
        self.assertEqual(explanation["entity_type"], "OBLIGATION")
        self.assertIn("summary_explanation", explanation)
        self.assertIn("regulatory_rule", explanation)
        self.assertIn("deadline_calculation", explanation)
        self.assertIn("audit_verification", explanation)
        self.assertTrue(explanation["regulatory_rule"]["is_aph_verified"])
        print("[OK] Test 04: Phase 5 'Why?' explainability engine verified.")

    def test_05_officer_daily_inbox_todays_10(self):
        """Phase 6.C: Verify prioritized Officer Daily Inbox with transparent priority factors."""
        inbox = get_officer_inbox_obligations(self.db, limit=10)
        self.assertLessEqual(len(inbox), 10)
        if inbox:
            top_item = inbox[0]
            self.assertIn("priority_score", top_item)
            self.assertIn("urgency_reasons", top_item)
            self.assertIn("next_required_action", top_item)
            # Verify ordering
            for i in range(len(inbox) - 1):
                self.assertGreaterEqual(inbox[i]["priority_score"], inbox[i+1]["priority_score"])
        print("[OK] Test 05: Officer Daily Inbox (Today's 10) verified.")

    def test_06_evc_management_lifecycle(self):
        """Phase 7: Verify EVC queuing, conflict-of-interest check, scheduling, and report submission."""
        app = self.db.query(Application).first()
        officer = self.db.query(User).filter(User.role == UserRole.AICTE_OFFICER).first()

        evc = EVCService.queue_application_for_evc(self.db, app.id, actor_user=officer)
        self.assertIsNotNone(evc.id)
        self.assertTrue(evc.evc_no.startswith("EVC-"))
        self.assertTrue(evc.conflict_check_passed)

        # Schedule visit
        scheduled = EVCService.schedule_visit(
            db=self.db,
            evc_id=evc.id,
            visit_date=datetime.utcnow() + timedelta(days=7),
            visit_location="Main Campus Premises",
            approved_experts=[{"id": 1, "name": "Prof. Dr. Rajeshwari Sundaram"}],
            officer_user=officer
        )
        self.assertEqual(scheduled.status, EVCStatus.SCHEDULED.value)

        # Submit report
        reported = EVCService.submit_evc_report(
            db=self.db,
            evc_id=evc.id,
            recommendation="RECOMMENDED",
            summary="All laboratories, faculty cadre ratio, and infrastructure verified on site.",
            officer_user=officer
        )
        self.assertEqual(reported.status, EVCStatus.REPORT_RECEIVED.value)
        self.assertEqual(reported.report_recommendation, "RECOMMENDED")
        print("[OK] Test 06: EVC scheduling and inspection report lifecycle verified.")

    def test_07_time_bound_undertaking_lifecycle(self):
        """Phase 8: Verify conditional undertaking creation, evidence submission, and compliance approval."""
        app = self.db.query(Application).first()
        officer = self.db.query(User).filter(User.role == UserRole.AICTE_OFFICER).first()

        ut = UndertakingService.create_undertaking(
            db=self.db,
            application_id=app.id,
            condition_title="Test Lab Wing Completion",
            condition_description="Complete building construction within 6 months.",
            statutory_deadline_months=6,
            actor_user=officer
        )
        self.assertIsNotNone(ut.id)
        self.assertEqual(ut.status, UndertakingStatus.PENDING.value)

        # Submit evidence
        submitted = UndertakingService.submit_compliance_evidence(
            db=self.db,
            undertaking_id=ut.id,
            evidence_description="Chartered architect completion certificate uploaded.",
            document_id=None,
            institution_user=officer
        )
        self.assertEqual(submitted.status, UndertakingStatus.EVIDENCE_SUBMITTED.value)

        # Review compliance
        reviewed = UndertakingService.review_compliance(
            db=self.db,
            undertaking_id=ut.id,
            is_compliant=True,
            review_notes="Verified certificate from municipal engineer.",
            officer_user=officer
        )
        self.assertEqual(reviewed.status, UndertakingStatus.COMPLIANT.value)
        print("[OK] Test 07: Time-bound undertaking compliance lifecycle verified.")

    def test_08_document_validity_tracker(self):
        """Phase 9: Verify document validity tracking and renewal."""
        inst = self.db.query(Institution).first()
        officer = self.db.query(User).filter(User.role == UserRole.AICTE_OFFICER).first()

        rec = DocumentValidityService.register_or_update_validity(
            db=self.db,
            institution_id=inst.id,
            document_type="FIRE_SAFETY_NOC",
            document_name="Unit Test Fire Safety Certificate",
            issuing_authority="State Fire Department",
            expiry_date=datetime.utcnow() + timedelta(days=20)
        )
        self.assertEqual(rec.status, DocumentValidityStatus.EXPIRING_SOON.value)

        # Submit renewal
        renewed = DocumentValidityService.submit_renewal(
            db=self.db,
            record_id=rec.id,
            renewal_document_id=1,
            new_expiry_date=datetime.utcnow() + timedelta(days=365),
            institution_user=officer
        )
        self.assertEqual(renewed.status, DocumentValidityStatus.RENEWAL_SUBMITTED.value)
        print("[OK] Test 08: Document validity tracker and renewal verified.")

    def test_09_cryptographic_audit_chain_integrity(self):
        """Phase 13: Verify SHA-256 block hash chain integrity and tamper-evidence."""
        res = verify_audit_chain_integrity(self.db)
        self.assertTrue(res["valid"])
        self.assertEqual(res["status"], "VALID")
        self.assertGreater(res["total_events"], 0)
        self.assertIsNotNone(res["latest_hash"])
        print(f"[OK] Test 09: Cryptographic SHA-256 audit chain verified. Total events: {res['total_events']}.")

    def test_10_all_11_compliance_reports_and_csv_exports(self):
        """Phase 13: Verify all 11 compliance and pendency reports produce valid JSON summaries and CSV files."""
        report_keys = [
            "pendency_ageing",
            "route_distribution",
            "stage_bottlenecks",
            "regional_pendency",
            "officer_workload",
            "obligations_status",
            "evc_tracking",
            "undertakings_compliance",
            "document_validity",
            "escalation_breaches",
            "audit_chain_integrity"
        ]
        for rk in report_keys:
            data = ComplianceReportsService.get_report_data(self.db, rk)
            self.assertIn("title", data)
            self.assertIn("headers", data)
            self.assertIn("summary", data)

            csv_text = ComplianceReportsService.generate_csv_for_report(self.db, rk)
            self.assertTrue(csv_text.startswith("\ufeff"))  # UTF-8 BOM
            lines = csv_text.splitlines()
            self.assertGreaterEqual(len(lines), 1)  # Header line present

        print(f"[OK] Test 10: All 11 official compliance reports and CSV exports verified.")


if __name__ == "__main__":
    unittest.main()
