import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.application import Application
from app.models.document import Document
from app.schemas.all_schemas import LoginRequest, RegisterRequest
from app.api.v1.auth import login, register_institution, get_current_user_profile
from app.api.v1.applications import list_applications, get_application_detail
from app.api.v1.trustgraph import get_application_trustgraph
from app.api.v1.validation import list_application_findings
from app.api.v1.documents import list_application_documents
from app.api.v1.verification import list_verification_sources
from app.api.v1.clarifications import list_application_clarifications
from app.api.v1.audit import check_audit_integrity
from app.api.v1.evaluation import run_evaluation_benchmark_suite
from app.api.v1.reports import export_application_csv, export_application_pdf


def test_all_route_handlers():
    print("=" * 70, flush=True)
    print("REGULENS AI — DIRECT FASTAPI ROUTE HANDLER VERIFICATION", flush=True)
    print("=" * 70, flush=True)

    db = SessionLocal()
    try:
        # 1. Auth: Login
        req = LoginRequest(email="officer@aicte-india.org", password="Officer@123")
        token_resp = login(req, db)
        assert token_resp["role"] == "AICTE_OFFICER"
        print(f"  [PASS] auth.login -> Officer: {token_resp['full_name']}", flush=True)

        officer = db.query(User).filter(User.email == "officer@aicte-india.org").first()
        inst_user = db.query(User).filter(User.email == "apex@institution.edu.in").first()

        # 2. Auth: Profile Me
        profile = get_current_user_profile(officer, db)
        assert profile["role"] == "AICTE_OFFICER"
        print(f"  [PASS] auth.get_current_user_profile -> {profile['full_name']}", flush=True)

        # 3. Applications: List
        apps = list_applications(None, None, None, officer, db)
        assert len(apps) >= 3
        print(f"  [PASS] applications.list_applications (Officer) -> {len(apps)} applications", flush=True)

        apex_apps = list_applications(None, None, None, inst_user, db)
        assert len(apex_apps) >= 1
        print(f"  [PASS] applications.list_applications (Institution) -> {len(apex_apps)} isolated app(s)", flush=True)

        # 4. Applications: Detail
        app_id = apps[0]["id"]
        app_detail = get_application_detail(app_id, officer, db)
        assert app_detail["reference_no"] is not None
        print(f"  [PASS] applications.get_application -> {app_detail['reference_no']}", flush=True)

        # 5. TrustGraph Endpoint
        tg = get_application_trustgraph(app_id, officer, db)
        assert len(tg["nodes"]) > 0
        assert len(tg["edges"]) > 0
        assert "finding_paths" in tg
        assert "contradictory_claims" in tg
        assert "duplicate_candidates" in tg
        assert "relationship_table" in tg
        assert "extracted_claims" in tg
        print(f"  [PASS] trustgraph.get_application_trustgraph -> {len(tg['nodes'])} nodes across 5 tiers, {len(tg['edges'])} edges", flush=True)

        # 6. Findings
        findings = list_application_findings(app_id, False, officer, db)
        print(f"  [PASS] validation.list_application_findings -> {len(findings)} findings", flush=True)

        # 7. Documents List
        docs = list_application_documents(app_id, officer, db)
        assert len(docs) > 0
        print(f"  [PASS] documents.list_application_documents -> {len(docs)} documents", flush=True)

        # 8. Verification Sources
        sources = list_verification_sources(officer, db)
        assert len(sources) >= 3
        print(f"  [PASS] verification.list_verification_sources -> {len(sources)} sources", flush=True)

        # 9. Clarifications
        clarifications = list_application_clarifications(app_id, officer, db)
        print(f"  [PASS] clarifications.list_application_clarifications -> {len(clarifications)} items", flush=True)

        # 10. Audit Chain Verification
        audit_res = check_audit_integrity(officer, db)
        assert audit_res["valid"] is True
        print(f"  [PASS] audit.check_audit_integrity -> VALID (Events: {audit_res['total_events']})", flush=True)

        # 11. 13-Case Regulatory Benchmark Suite
        bench_res = run_evaluation_benchmark_suite(officer, db)
        assert bench_res["total_tests"] == 13
        assert bench_res["passed_tests"] == 13
        print(f"  [PASS] evaluation.run_evaluation_benchmark_suite -> 13/13 passed ({bench_res['pass_rate_percentage']}%)", flush=True)

        # 12. Reports Export
        csv_rep = export_application_csv(app_id, officer, db)
        assert len(csv_rep.body) > 100
        print(f"  [PASS] reports.export_application_csv -> {len(csv_rep.body)} bytes", flush=True)

        pdf_rep = export_application_pdf(app_id, officer, db)
        assert pdf_rep.status_code == 200
        print("  [PASS] reports.export_application_pdf -> StreamingResponse (PDF export 200 OK)", flush=True)

        # 13. Registration Route
        ts = int(time.time())
        reg_in = RegisterRequest(
            email=f"registrar_route_test_{ts}@nationaltech.edu.in",
            password="SecurePass@123",
            full_name="Prof. C. V. Raman",
            institution_name=f"Raman Institute of Technology {ts}",
            state="Tamil Nadu",
            district="Chennai",
            approved_intake=420,
            land_area_acres=8.0
        )
        reg_res = register_institution(reg_in, db)
        assert reg_res["role"] == "INSTITUTION_USER"
        print(f"  [PASS] auth.register_institution -> Token generated for {reg_in.email}", flush=True)

    finally:
        db.close()

    print("\n" + "=" * 70, flush=True)
    print("ALL 13 FASTAPI ROUTE HANDLERS PASSED CLEANLY WITH ZERO ERRORS!", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    test_all_route_handlers()
