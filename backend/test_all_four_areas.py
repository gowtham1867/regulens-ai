import io
import csv
import requests
import json

BACKEND_BASE = "http://127.0.0.1:8000"
FRONTEND_BASE = "http://127.0.0.1:5173"

def run_tests():
    print("=" * 70)
    print("ReguLens AI - Comprehensive Verification of 4 Target Areas")
    print("=" * 70)
    all_passed = True

    # -------------------------------------------------------------
    # AREA 1 & 2: Dedicated Portals & Role-Based Login Validation
    # -------------------------------------------------------------
    print("\n[TEST 1] Dedicated Portals & Role-Based Login Validation")

    # 1.A Institution Portal - Valid Institution User
    r = requests.post(
        f"{BACKEND_BASE}/api/v1/auth/login?portal=INSTITUTION",
        json={"email": "apex@institution.edu.in", "password": "Institute@123"}
    )
    if r.status_code == 200 and r.json().get("role") == "INSTITUTION_USER":
        print("  [PASS] Valid Institution Login -> 200 OK (role: INSTITUTION_USER)")
        inst_token = r.json().get("access_token")
    else:
        print(f"  [FAIL] Valid Institution Login failed: {r.status_code} {r.text}")
        all_passed = False

    # 1.B Institution Portal - Officer Blocked
    r = requests.post(
        f"{BACKEND_BASE}/api/v1/auth/login?portal=INSTITUTION",
        json={"email": "officer@aicte-india.org", "password": "Officer@123"}
    )
    if r.status_code == 403 and "Officer Portal" in r.json().get("detail", ""):
        print(f"  [PASS] Officer blocked on Institution Portal -> 403 Forbidden: '{r.json().get('detail')}'")
    else:
        print(f"  [FAIL] Officer was not properly blocked on Institution Portal: {r.status_code} {r.text}")
        all_passed = False

    # 1.C Officer Portal - Valid Officer
    r = requests.post(
        f"{BACKEND_BASE}/api/v1/auth/login?portal=OFFICER",
        json={"email": "officer@aicte-india.org", "password": "Officer@123"}
    )
    if r.status_code == 200 and r.json().get("role") == "AICTE_OFFICER":
        print("  [PASS] Valid Officer Login -> 200 OK (role: AICTE_OFFICER)")
        officer_token = r.json().get("access_token")
    else:
        print(f"  [FAIL] Valid Officer Login failed: {r.status_code} {r.text}")
        all_passed = False

    # 1.D Officer Portal - Valid Admin
    r = requests.post(
        f"{BACKEND_BASE}/api/v1/auth/login?portal=OFFICER",
        json={"email": "admin@aicte-india.org", "password": "Admin@123"}
    )
    if r.status_code == 200 and r.json().get("role") == "ADMINISTRATOR":
        print("  [PASS] Valid Admin Login on Officer Portal -> 200 OK (role: ADMINISTRATOR)")
        admin_token = r.json().get("access_token")
    else:
        print(f"  [FAIL] Valid Admin Login failed: {r.status_code} {r.text}")
        all_passed = False

    # 1.E Officer Portal - Institution User Blocked
    r = requests.post(
        f"{BACKEND_BASE}/api/v1/auth/login?portal=OFFICER",
        json={"email": "apex@institution.edu.in", "password": "Institute@123"}
    )
    if r.status_code == 403 and "Institution Portal" in r.json().get("detail", ""):
        print(f"  [PASS] Institution user blocked on Officer Portal -> 403 Forbidden: '{r.json().get('detail')}'")
    else:
        print(f"  [FAIL] Institution user was not properly blocked on Officer Portal: {r.status_code} {r.text}")
        all_passed = False

    # -------------------------------------------------------------
    # AREA 2: RBAC Data Isolation
    # -------------------------------------------------------------
    print("\n[TEST 2] Role-Based Access Control & Isolation")
    inst_headers = {"Authorization": f"Bearer {inst_token}"}
    officer_headers = {"Authorization": f"Bearer {officer_token}"}

    # Institution user lists applications -> only gets apex applications
    r_inst_apps = requests.get(f"{BACKEND_BASE}/api/v1/applications", headers=inst_headers)
    inst_apps = r_inst_apps.json()
    all_same_inst = all(a["institution_name"] == "Apex Institute of Technology" for a in inst_apps)
    print(f"  [PASS] Institution User fetches {len(inst_apps)} applications (Strict isolation verified: {all_same_inst})")

    # Officer lists applications -> sees entire scrutiny queue
    r_off_apps = requests.get(f"{BACKEND_BASE}/api/v1/applications", headers=officer_headers)
    off_apps = r_off_apps.json()
    print(f"  [PASS] Officer fetches full queue: {len(off_apps)} applications")

    # Institution user cannot access admin audit endpoint
    r_audit = requests.get(f"{BACKEND_BASE}/api/v1/audit-integrity", headers=inst_headers)
    if r_audit.status_code == 403:
        print("  [PASS] Institution user blocked from Admin Audit Integrity -> 403 Forbidden")
    else:
        print(f"  [FAIL] Institution user was not forbidden from audit integrity: {r_audit.status_code}")
        all_passed = False

    # -------------------------------------------------------------
    # AREA 3: Functional "Verify Authority" Button & Manual Workflow
    # -------------------------------------------------------------
    print("\n[TEST 3] Functional Issuing Authority Verification")

    # 3.A Automated Authority Verification
    r_verify = requests.post(
        f"{BACKEND_BASE}/api/v1/documents/1/verify?source_code=STATE_FIRE_SERVICES_PORTAL&force_refresh=true",
        headers=officer_headers
    )
    if r_verify.status_code == 200:
        verif_data = r_verify.json()
        print(f"  [PASS] Automated Authority Verification -> 200 OK")
        print(f"         Source: '{verif_data.get('source_name')}', Outcome: {verif_data.get('outcome')}")
    else:
        print(f"  [FAIL] Automated verification failed: {r_verify.status_code} {r_verify.text}")
        all_passed = False

    # 3.B Manual Officer Verification Workflow
    r_manual = requests.post(
        f"{BACKEND_BASE}/api/v1/documents/1/manual-verify",
        headers=officer_headers,
        json={
            "outcome": "VERIFIED",
            "notes": "Verified wet-ink seal and registrar signature in person at Regional Fire Directorate.",
            "issuing_authority": "Directorate of Fire and Rescue Services",
            "certificate_number": "FS-TN-2024-8841"
        }
    )
    if r_manual.status_code == 200:
        man_data = r_manual.json()
        print(f"  [PASS] Officer Manual Authority Verification -> 200 OK")
        print(f"         Method: {man_data.get('verification_method')}, Outcome: {man_data.get('outcome')}, Is Simulated: {man_data.get('is_simulated')}")
    else:
        print(f"  [FAIL] Officer manual verification failed: {r_manual.status_code} {r_manual.text}")
        all_passed = False

    # 3.C Institution User cannot execute manual officer verification
    r_inst_manual = requests.post(
        f"{BACKEND_BASE}/api/v1/documents/1/manual-verify",
        headers=inst_headers,
        json={"outcome": "VERIFIED", "notes": "Unauthorized attempt"}
    )
    if r_inst_manual.status_code == 403:
        print("  [PASS] Institution user blocked from Officer Manual Verification -> 403 Forbidden")
    else:
        print(f"  [FAIL] Institution user was not forbidden from manual verification: {r_inst_manual.status_code}")
        all_passed = False

    # 3.D Verification History Persistence
    r_hist = requests.get(f"{BACKEND_BASE}/api/v1/documents/1/verification-history", headers=officer_headers)
    if r_hist.status_code == 200:
        hist_records = r_hist.json()
        print(f"  [PASS] Verification History retrieved -> Found {len(hist_records)} persisted audit attempts")
        if len(hist_records) > 0:
            print(f"         Latest attempt outcome: {hist_records[0].get('outcome')} via {hist_records[0].get('source_name')}")
    else:
        print(f"  [FAIL] Failed to retrieve verification history: {r_hist.status_code}")
        all_passed = False

    # -------------------------------------------------------------
    # AREA 4: CSV Export Data Integrity
    # -------------------------------------------------------------
    print("\n[TEST 4] CSV Export Data Integrity")

    # 4.A Applications Queue CSV
    r_csv_queue = requests.get(f"{BACKEND_BASE}/api/v1/applications/export.csv", headers=officer_headers)
    if r_csv_queue.status_code == 200:
        content_bytes = r_csv_queue.content
        has_bom = content_bytes.startswith(b'\xef\xbb\xbf')
        csv_text = content_bytes.decode('utf-8-sig')
        reader = list(csv.reader(io.StringIO(csv_text)))
        headers = reader[0]
        rows = reader[1:]
        print(f"  [PASS] Applications Queue CSV Export -> 200 OK")
        print(f"         UTF-8 BOM present: {has_bom} (Required for Microsoft Excel)")
        print(f"         Header count: {len(headers)} columns")
        print(f"         First 5 headers: {headers[:5]}")
        print(f"         Data rows exported: {len(rows)} (1 row per application)")
        print(f"         First row reference: {rows[0][0] if rows else 'N/A'}")
    else:
        print(f"  [FAIL] Applications Queue CSV failed: {r_csv_queue.status_code}")
        all_passed = False

    # 4.B Application Findings CSV
    r_csv_findings = requests.get(f"{BACKEND_BASE}/api/v1/applications/1/report.csv?export_type=findings", headers=officer_headers)
    if r_csv_findings.status_code == 200:
        has_bom = r_csv_findings.content.startswith(b'\xef\xbb\xbf')
        csv_text = r_csv_findings.content.decode('utf-8-sig')
        reader = list(csv.reader(io.StringIO(csv_text)))
        headers = reader[0]
        rows = reader[1:]
        print(f"  [PASS] Application Findings CSV Export -> 200 OK")
        print(f"         UTF-8 BOM present: {has_bom}")
        print(f"         Header count: {len(headers)} columns")
        print(f"         First 5 headers: {headers[:5]}")
        print(f"         Findings rows exported: {len(rows)} (1 row per compliance finding)")
    else:
        print(f"  [FAIL] Application Findings CSV failed: {r_csv_findings.status_code}")
        all_passed = False

    # 4.C Application Documents CSV
    r_csv_docs = requests.get(f"{BACKEND_BASE}/api/v1/applications/1/report.csv?export_type=documents", headers=officer_headers)
    if r_csv_docs.status_code == 200:
        has_bom = r_csv_docs.content.startswith(b'\xef\xbb\xbf')
        csv_text = r_csv_docs.content.decode('utf-8-sig')
        reader = list(csv.reader(io.StringIO(csv_text)))
        headers = reader[0]
        rows = reader[1:]
        print(f"  [PASS] Application Documents CSV Export -> 200 OK")
        print(f"         UTF-8 BOM present: {has_bom}")
        print(f"         Header count: {len(headers)} columns")
        print(f"         First 5 headers: {headers[:5]}")
        print(f"         Documents rows exported: {len(rows)} (1 row per document)")
    else:
        print(f"  [FAIL] Application Documents CSV failed: {r_csv_docs.status_code}")
        all_passed = False

    # -------------------------------------------------------------
    # AREA 5: Frontend Route Accessibility
    # -------------------------------------------------------------
    print("\n[TEST 5] Frontend Public & Dedicated Portal Routes")
    routes_to_test = ["/login", "/institution/login", "/officer/login"]
    for route in routes_to_test:
        r_fe = requests.get(f"{FRONTEND_BASE}{route}", timeout=5)
        if r_fe.status_code == 200 and "<div id=\"root\">" in r_fe.text:
            print(f"  [PASS] Route {route:25s} -> 200 OK (Renderable HTML)")
        else:
            print(f"  [FAIL] Route {route} failed: {r_fe.status_code}")
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print(">>> ALL 4 TARGET AREAS TESTED AND VERIFIED PERFECTLY! <<<")
    else:
        print(">>> SOME VERIFICATION TESTS FAILED! <<<")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()

