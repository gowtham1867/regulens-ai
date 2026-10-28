import pytest
from app.database import SessionLocal
from app.services.audit_service import verify_audit_chain_integrity
from app.services.evaluation_service import EvaluationBenchmarkService


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "ReguLens" in data["service"]


def test_auth_success_and_role_tokens(client):
    # 1. Officer Login
    res_officer = client.post("/api/v1/auth/login", json={
        "email": "officer@aicte-india.org",
        "password": "Officer@123"
    })
    assert res_officer.status_code == 200
    data = res_officer.json()
    assert data["role"] == "AICTE_OFFICER"
    assert "access_token" in data

    # 2. Institution Login
    res_inst = client.post("/api/v1/auth/login", json={
        "email": "apex@institution.edu.in",
        "password": "Institute@123"
    })
    assert res_inst.status_code == 200
    data_inst = res_inst.json()
    assert data_inst["role"] == "INSTITUTION_USER"
    assert data_inst["institution_name"] == "Apex Institute of Technology & Engineering"


def test_auth_invalid_credentials(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "officer@aicte-india.org",
        "password": "WrongPassword123!"
    })
    assert res.status_code == 401


def test_applications_role_isolation(client):
    # Login as Apex user
    res_apex = client.post("/api/v1/auth/login", json={
        "email": "apex@institution.edu.in",
        "password": "Institute@123"
    })
    token_apex = res_apex.json()["access_token"]

    # Apex user gets applications - should only see Apex applications
    res_apps = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {token_apex}"})
    assert res_apps.status_code == 200
    apps = res_apps.json()
    assert len(apps) >= 1
    for a in apps:
        assert "Apex" in a["institution_name"]

    # Officer sees all applications
    res_off = client.post("/api/v1/auth/login", json={
        "email": "officer@aicte-india.org",
        "password": "Officer@123"
    })
    token_off = res_off.json()["access_token"]
    res_all_apps = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {token_off}"})
    assert res_all_apps.status_code == 200
    assert len(res_all_apps.json()) >= 3


def test_validation_engine_findings(client):
    res_off = client.post("/api/v1/auth/login", json={
        "email": "officer@aicte-india.org",
        "password": "Officer@123"
    })
    token = res_off.json()["access_token"]

    # Application 2 (Zenith) has known deficiencies
    res_findings = client.get("/api/v1/applications/2/findings", headers={"Authorization": f"Bearer {token}"})
    assert res_findings.status_code == 200
    findings = res_findings.json()
    assert len(findings) >= 2
    
    # Check for expired fire certificate finding
    expired_f = next((f for f in findings if f["rule_code"] == "AICTE-RULE-002-FIRE-VALIDITY"), None)
    assert expired_f is not None
    assert expired_f["status"] == "FAILED"
    assert "Expired" in expired_f["observed_value"]


def test_trustgraph_relationships(client):
    res_off = client.post("/api/v1/auth/login", json={
        "email": "officer@aicte-india.org",
        "password": "Officer@123"
    })
    token = res_off.json()["access_token"]

    res_graph = client.get("/api/v1/applications/1/trustgraph", headers={"Authorization": f"Bearer {token}"})
    assert res_graph.status_code == 200
    graph = res_graph.json()
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) >= 5
    assert len(graph["edges"]) >= 4

    node_types = set(n["type"] for n in graph["nodes"])
    assert "INSTITUTION" in node_types
    assert "APPLICATION" in node_types
    assert "DOCUMENT" in node_types
    assert "REGULATORY_RULE" in node_types


def test_verification_cache_and_adapter(client):
    res_off = client.post("/api/v1/auth/login", json={
        "email": "officer@aicte-india.org",
        "password": "Officer@123"
    })
    token = res_off.json()["access_token"]

    # Verify Fire document for Application 1
    res = client.post(
        "/api/v1/documents/1/verify?source_code=STATE_FIRE_SERVICES_PORTAL",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["outcome"] == "VERIFIED"
    assert data["is_simulated"] is True


def test_tamper_evident_audit_chain():
    db = SessionLocal()
    try:
        integrity = verify_audit_chain_integrity(db)
        assert integrity["valid"] is True
        assert integrity["status"] in ["VALID", "EMPTY"]
    finally:
        db.close()


def test_13_case_evaluation_suite():
    db = SessionLocal()
    try:
        service = EvaluationBenchmarkService(db)
        report = service.run_13_case_evaluation_suite()
        assert report["total_tests"] == 13
        assert report["passed_tests"] >= 10
        assert report["pass_rate_percentage"] > 70.0
    finally:
        db.close()

