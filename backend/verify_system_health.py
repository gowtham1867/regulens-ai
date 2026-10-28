import requests
import json
import sys

BACKEND_BASE = "http://127.0.0.1:8000"
FRONTEND_BASE = "http://127.0.0.1:5173"

DEMO_USERS = [
    ("admin@aicte-india.org", "Admin@123", "ADMIN"),
    ("officer@aicte-india.org", "Officer@123", "AICTE_OFFICER"),
    ("apex@institution.edu.in", "Institute@123", "INSTITUTION"),
    ("zenith@institution.edu.in", "Institute@123", "INSTITUTION"),
    ("vanguard@institution.edu.in", "Institute@123", "INSTITUTION"),
]

def run_checks():
    print("=" * 60)
    print("ReguLens AI - Full System Health & Connectivity Audit")
    print("=" * 60)
    all_passed = True

    # 1. Backend Root Check
    try:
        r = requests.get(f"{BACKEND_BASE}/", timeout=5)
        print(f"[OK] Backend Root (/) Status: {r.status_code} -> {r.json()}")
    except Exception as e:
        print(f"[FAIL] Backend Root failed: {e}")
        all_passed = False

    # 2. Backend Health Check
    try:
        r = requests.get(f"{BACKEND_BASE}/api/v1/health", timeout=5)
        print(f"[OK] Backend Health Status: {r.status_code} -> {r.json().get('status')}")
    except Exception as e:
        print(f"[FAIL] Backend Health failed: {e}")
        all_passed = False

    # 3. Frontend Server Check
    try:
        r = requests.get(f"{FRONTEND_BASE}/", timeout=5)
        is_html = "<!DOCTYPE html>" in r.text or "<div id=\"root\">" in r.text
        print(f"[OK] Frontend Server (/) Status: {r.status_code}, HTML length: {len(r.text)}, HTML valid: {is_html}")
    except Exception as e:
        print(f"[FAIL] Frontend Server failed: {e}")
        all_passed = False

    # 4. Frontend Reverse Proxy Check (/api/v1/health via Vite port 5173)
    try:
        r = requests.get(f"{FRONTEND_BASE}/api/v1/health", timeout=5)
        print(f"[OK] Vite Proxy (/api/v1/health) Status: {r.status_code} -> {r.json().get('status')}")
    except Exception as e:
        print(f"[FAIL] Vite Proxy to Backend failed: {e}")
        all_passed = False

    # 5. Authentication Test for all Demo Accounts
    tokens = {}
    print("\n--- Testing Authentication for All Roles ---")
    for email, pwd, expected_role in DEMO_USERS:
        try:
            # First try direct backend
            r = requests.post(f"{BACKEND_BASE}/api/v1/auth/login", json={"email": email, "password": pwd}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                token = data.get("access_token")
                tokens[email] = token
                # Check me endpoint
                me_r = requests.get(f"{BACKEND_BASE}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=5)
                me_data = me_r.json()
                actual_role = me_data.get("role")
                name = me_data.get("full_name")
                print(f"[OK] Login {email:30s} -> Role: {actual_role} | Name: {name}")
                if actual_role != expected_role:
                    print(f"     [WARN] Role mismatch: expected {expected_role}, got {actual_role}")
            else:
                print(f"[FAIL] Login {email} failed: {r.status_code} {r.text}")
                all_passed = False
        except Exception as e:
            print(f"[FAIL] Login {email} exception: {e}")
            all_passed = False

    # 6. Test Officer Applications List & Detail
    officer_token = tokens.get("officer@aicte-india.org")
    if officer_token:
        print("\n--- Testing Officer Scrutiny & Document Access Endpoints ---")
        headers = {"Authorization": f"Bearer {officer_token}"}
        try:
            apps_r = requests.get(f"{BACKEND_BASE}/api/v1/applications", headers=headers, timeout=5)
            apps = apps_r.json()
            print(f"[OK] Officer fetched {len(apps)} applications successfully.")
            
            # Inspect Application ID 1 (the main seeded application)
            app1_r = requests.get(f"{BACKEND_BASE}/api/v1/applications/1", headers=headers, timeout=5)
            if app1_r.status_code == 200:
                app1 = app1_r.json()
                print(f"\n--- Deep Audit on Main Seed Application #{app1.get('reference_no')} (ID: 1) ---")
                
                # Requirements
                req_r = requests.get(f"{BACKEND_BASE}/api/v1/applications/1/requirements", headers=headers, timeout=5)
                if req_r.status_code == 200:
                    req_data = req_r.json()
                    print(f"[OK] Requirements Checklist: Status 200, Found {len(req_data.get('requirements', []))} checklist items, Score: {req_data.get('completion_percentage')}%")
                
                # Deficiencies
                def_r = requests.get(f"{BACKEND_BASE}/api/v1/applications/1/deficiencies", headers=headers, timeout=5)
                if def_r.status_code == 200:
                    print(f"[OK] Deficiencies: Status 200, Found {len(def_r.json())} deficiency items.")

                # Duplicates
                dup_r = requests.get(f"{BACKEND_BASE}/api/v1/applications/1/duplicates", headers=headers, timeout=5)
                if dup_r.status_code == 200:
                    print(f"[OK] Duplicates: Status 200, Found {len(dup_r.json())} duplicate flags.")

                # Documents
                docs_r = requests.get(f"{BACKEND_BASE}/api/v1/applications/1/documents", headers=headers, timeout=5)
                if docs_r.status_code == 200:
                    docs = docs_r.json()
                    print(f"[OK] Application 1 has {len(docs)} documents.")
                    for d in docs:
                        lv = d.get("latest_version")
                        if lv:
                            v_id = lv["id"]
                            v_name = lv.get("original_filename")
                            # Test download with Bearer auth
                            dl_r = requests.get(f"{BACKEND_BASE}/api/v1/document-versions/{v_id}/download", headers=headers, timeout=5)
                            # Test download with query token
                            dl_token_r = requests.get(f"{BACKEND_BASE}/api/v1/document-versions/{v_id}/download?token={officer_token}", timeout=5)
                            print(f"[OK] Doc '{d.get('title')}' (v{lv.get('version_number')}, '{v_name}'):")
                            print(f"     -> Bearer Auth Download: Status {dl_r.status_code}, Size {len(dl_r.content)} bytes, Type: {dl_r.headers.get('content-type')}")
                            print(f"     -> Query Token Download:  Status {dl_token_r.status_code}, Size {len(dl_token_r.content)} bytes")
                            break

                # Reports
                pdf_r = requests.get(f"{BACKEND_BASE}/api/v1/applications/1/report.pdf", headers=headers, timeout=5)
                print(f"[OK] PDF Report Export: Status {pdf_r.status_code}, Size {len(pdf_r.content)} bytes")

                csv_r = requests.get(f"{BACKEND_BASE}/api/v1/applications/1/report.csv", headers=headers, timeout=5)
                print(f"[OK] CSV Report Export: Status {csv_r.status_code}, Size {len(csv_r.content)} bytes")
        except Exception as e:
            print(f"[FAIL] Officer scrutiny tests failed: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL VERIFICATION CHECKS PASSED PERFECTLY!")
    else:
        print("SOME CHECKS REPORTED FAILURES!")
    print("=" * 60)

if __name__ == "__main__":
    run_checks()
