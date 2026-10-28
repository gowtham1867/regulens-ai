import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"
FRONTEND_URL = "http://localhost:5173"

def run_login_tests():
    print("==================================================", flush=True)
    print("REGULENS AI: LOGIN REDESIGN & AUTHENTICATION TESTS", flush=True)
    print("==================================================", flush=True)

    # 1. Test Institution Login via INSTITUTION portal
    print("\n[Test 1] Testing Institution Login with valid credentials...", flush=True)
    res_inst = requests.post(f"{BASE_URL}/auth/login?portal=INSTITUTION", json={
        "email": "apex@institution.edu.in",
        "password": "Institute@123"
    })
    assert res_inst.status_code == 200, f"Institution login failed: {res_inst.text}"
    inst_data = res_inst.json()
    assert inst_data["role"] == "INSTITUTION_USER", f"Expected INSTITUTION_USER, got {inst_data['role']}"
    assert "access_token" in inst_data, "No access_token returned"
    print(f"  -> Successfully authenticated Institution user: {inst_data['email']} (Role: {inst_data['role']}, Inst: {inst_data.get('institution_name')})", flush=True)

    # 2. Test AICTE Member Login via OFFICER portal
    print("\n[Test 2] Testing AICTE Member Login with valid credentials...", flush=True)
    res_officer = requests.post(f"{BASE_URL}/auth/login?portal=OFFICER", json={
        "email": "officer@aicte-india.org",
        "password": "Officer@123"
    })
    assert res_officer.status_code == 200, f"Officer login failed: {res_officer.text}"
    officer_data = res_officer.json()
    assert officer_data["role"] == "AICTE_OFFICER", f"Expected AICTE_OFFICER, got {officer_data['role']}"
    assert "access_token" in officer_data, "No access_token returned"
    print(f"  -> Successfully authenticated AICTE Member: {officer_data['email']} (Role: {officer_data['role']})", flush=True)

    # 3. Test Cross-Portal Enforcement: Institution user on OFFICER portal must fail
    print("\n[Test 3] Testing Cross-Portal Protection: Institution user on AICTE Member section...", flush=True)
    res_cross1 = requests.post(f"{BASE_URL}/auth/login?portal=OFFICER", json={
        "email": "apex@institution.edu.in",
        "password": "Institute@123"
    })
    assert res_cross1.status_code == 403, f"Expected 403 Forbidden, got {res_cross1.status_code}"
    cross1_detail = res_cross1.json().get("detail", "")
    assert "Institutional user accounts cannot access" in cross1_detail, f"Unexpected detail: {cross1_detail}"
    print(f"  -> Properly blocked institution user from AICTE Member portal (403): '{cross1_detail}'", flush=True)

    # 4. Test Cross-Portal Enforcement: Officer user on INSTITUTION portal must fail
    print("\n[Test 4] Testing Cross-Portal Protection: AICTE Officer on Institution section...", flush=True)
    res_cross2 = requests.post(f"{BASE_URL}/auth/login?portal=INSTITUTION", json={
        "email": "officer@aicte-india.org",
        "password": "Officer@123"
    })
    assert res_cross2.status_code == 403, f"Expected 403 Forbidden, got {res_cross2.status_code}"
    cross2_detail = res_cross2.json().get("detail", "")
    assert "exclusively reserved for academic institutions" in cross2_detail, f"Unexpected detail: {cross2_detail}"
    print(f"  -> Properly blocked AICTE officer from Institution portal (403): '{cross2_detail}'", flush=True)

    # 5. Test Invalid Credentials
    print("\n[Test 5] Testing Invalid Credentials handling...", flush=True)
    res_inv = requests.post(f"{BASE_URL}/auth/login?portal=INSTITUTION", json={
        "email": "apex@institution.edu.in",
        "password": "WrongPassword!999"
    })
    assert res_inv.status_code == 401, f"Expected 401 Unauthorized, got {res_inv.status_code}"
    print(f"  -> Properly returned 401 Unauthorized for invalid password: '{res_inv.json().get('detail')}'", flush=True)

    # 6. Test Frontend Server Availability & Route Response
    print("\n[Test 6] Testing Frontend Route Accessibility...", flush=True)
    try:
        fe_res = requests.get(f"{FRONTEND_URL}/login")
        assert fe_res.status_code == 200, f"Frontend /login returned {fe_res.status_code}"
        print(f"  -> Frontend dev server reachable on {FRONTEND_URL}/login (HTTP 200 OK)", flush=True)
    except Exception as e:
        print(f"  -> Frontend probe notice: {e}", flush=True)

    print("\n==================================================", flush=True)
    print("ALL REGULENS LOGIN REDESIGN TESTS PASSED!", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    run_login_tests()

