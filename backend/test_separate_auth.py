import uuid
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_auth_and_registration():
    print("==================================================", flush=True)
    print("REGULENS AI: SEPARATE AUTH & REGISTRATION TESTS", flush=True)
    print("==================================================", flush=True)

    # 1. Institution Portal Login
    print("\n[Step 1] Testing Institution Login on INSTITUTION Portal...", flush=True)
    inst_login = requests.post(f"{BASE_URL}/auth/login?portal=INSTITUTION", json={
        "email": "apex@institution.edu.in",
        "password": "Institute@123"
    })
    assert inst_login.status_code == 200, f"Expected 200, got {inst_login.status_code}: {inst_login.text}"
    inst_data = inst_login.json()
    assert inst_data["role"] == "INSTITUTION_USER", f"Expected INSTITUTION_USER, got {inst_data['role']}"
    print("  [OK] Institution login succeeded. Role: INSTITUTION_USER", flush=True)

    # 2. Cross-portal rejection: Officer on Institution Portal
    print("\n[Step 2] Testing Officer attempting to sign in on INSTITUTION Portal...", flush=True)
    officer_on_inst = requests.post(f"{BASE_URL}/auth/login?portal=INSTITUTION", json={
        "email": "officer@aicte-india.org",
        "password": "Officer@123"
    })
    assert officer_on_inst.status_code == 403, f"Expected 403, got {officer_on_inst.status_code}"
    assert "AICTE Officer" in officer_on_inst.json()["detail"], "Expected officer redirect guidance in error message"
    print(f"  [OK] Officer correctly blocked from Institution Portal: {officer_on_inst.json()['detail']}", flush=True)

    # 3. Officer Portal Login
    print("\n[Step 3] Testing AICTE Member Login on OFFICER Portal...", flush=True)
    officer_login = requests.post(f"{BASE_URL}/auth/login?portal=OFFICER", json={
        "email": "officer@aicte-india.org",
        "password": "Officer@123"
    })
    assert officer_login.status_code == 200, f"Expected 200, got {officer_login.status_code}"
    officer_data = officer_login.json()
    assert officer_data["role"] == "AICTE_OFFICER", f"Expected AICTE_OFFICER, got {officer_data['role']}"
    officer_token = officer_data["access_token"]
    officer_headers = {"Authorization": f"Bearer {officer_token}"}
    print("  [OK] AICTE Officer login succeeded. Role: AICTE_OFFICER", flush=True)

    # 4. Cross-portal rejection: Institution on Officer Portal
    print("\n[Step 4] Testing Institution user attempting to sign in on OFFICER Portal...", flush=True)
    inst_on_officer = requests.post(f"{BASE_URL}/auth/login?portal=OFFICER", json={
        "email": "apex@institution.edu.in",
        "password": "Institute@123"
    })
    assert inst_on_officer.status_code == 403, f"Expected 403, got {inst_on_officer.status_code}"
    assert "Institutional user accounts cannot access" in inst_on_officer.json()["detail"]
    print(f"  [OK] Institution correctly blocked from Officer Portal: {inst_on_officer.json()['detail']}", flush=True)

    # 5. Password length validation
    print("\n[Step 5] Testing password strength validation on registration (< 8 chars)...", flush=True)
    short_pw_res = requests.post(f"{BASE_URL}/auth/register", json={
        "institution_name": "Short Pass Univ",
        "full_name": "Test User",
        "email": f"short_{uuid.uuid4().hex[:6]}@test.edu",
        "password": "short"
    })
    assert short_pw_res.status_code == 400, f"Expected 400, got {short_pw_res.status_code}"
    assert "at least 8 characters" in short_pw_res.json()["detail"]
    print("  [OK] Short password rejected with validation error", flush=True)

    # 6. Institution Registration Lifecycle
    unique_tag = uuid.uuid4().hex[:6]
    inst_name = f"Indian Institute of Advanced AI & Cybernetics ({unique_tag})"
    reg_email = f"director_{unique_tag}@iiac.ac.in"
    print(f"\n[Step 6] Registering new institution: '{inst_name}'...", flush=True)

    reg_payload = {
        "institution_name": inst_name,
        "institution_type": "ENGINEERING_AND_TECHNOLOGY",
        "address": "404 Innovation Way, Tech Park",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "pin_code": "560001",
        "institution_email": f"contact_{unique_tag}@iiac.ac.in",
        "contact_phone": "9876543210",
        "full_name": f"Prof. Rajesh Nambiar {unique_tag}",
        "designation": "Director & Principal",
        "email": reg_email,
        "password": "CompliantPassword@2026",
        "phone": "9876543210"
    }

    reg_res = requests.post(f"{BASE_URL}/auth/register", json=reg_payload)
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert reg_data["approval_status"] == "PENDING_VERIFICATION", f"Expected PENDING_VERIFICATION, got {reg_data['approval_status']}"
    new_inst_id = reg_data["institution_id"]
    print(f"  [OK] Registration created successfully! Institution ID={new_inst_id}, Status={reg_data['approval_status']}", flush=True)

    # 7. Duplicate email prevention
    print("\n[Step 7] Testing duplicate account prevention...", flush=True)
    dup_res = requests.post(f"{BASE_URL}/auth/register", json={
        "institution_name": f"Another Name {unique_tag}",
        "full_name": "Another Registrar",
        "email": reg_email,
        "password": "CompliantPassword@2026"
    })
    assert dup_res.status_code == 400, f"Expected 400 for duplicate email, got {dup_res.status_code}"
    print(f"  [OK] Duplicate account prevented: {dup_res.json()['detail']}", flush=True)

    # 8. AICTE Officer inspects pending institutions
    print("\n[Step 8] AICTE Officer inspecting pending registrations...", flush=True)
    pending_res = requests.get(f"{BASE_URL}/auth/institutions/pending", headers=officer_headers)
    assert pending_res.status_code == 200, f"Failed to get pending list: {pending_res.text}"
    pending_list = pending_res.json()
    found = [p for p in pending_list if p["id"] == new_inst_id]
    assert len(found) > 0, f"Newly registered institution {new_inst_id} was not in pending list!"
    print(f"  [OK] Officer found pending institution '{found[0]['name']}' ({found[0]['aicte_id']})", flush=True)

    # 9. Officer verifies and approves the institution
    print(f"\n[Step 9] Officer approving institution ID={new_inst_id}...", flush=True)
    verify_res = requests.patch(
        f"{BASE_URL}/auth/institutions/{new_inst_id}/verify",
        headers=officer_headers,
        json={"approval_status": "APPROVED"}
    )
    assert verify_res.status_code == 200, f"Failed to verify institution: {verify_res.text}"
    assert verify_res.json()["approval_status"] == "APPROVED"
    print(f"  [OK] Officer approved institution. Updated status: {verify_res.json()['approval_status']}", flush=True)

    # 10. Newly verified institution logs in
    print("\n[Step 10] Newly verified institution signing in...", flush=True)
    new_login = requests.post(f"{BASE_URL}/auth/login?portal=INSTITUTION", json={
        "email": reg_email,
        "password": "CompliantPassword@2026"
    })
    assert new_login.status_code == 200, f"Failed to login: {new_login.text}"
    assert new_login.json()["approval_status"] == "APPROVED"
    print(f"  [OK] Verified institution logged in successfully with status: {new_login.json()['approval_status']}", flush=True)

    print("\n==================================================", flush=True)
    print("ALL SEPARATE AUTH & REGISTRATION TESTS PASSED! 10/10", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    test_auth_and_registration()
