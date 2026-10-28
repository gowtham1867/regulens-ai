import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

def run_tests():
    print("==================================================", flush=True)
    print("REGULENS AI: APPROVAL WORKFLOW & NOTIFICATIONS E2E", flush=True)
    print("==================================================", flush=True)

    # 1. Login AICTE Officer
    print("\n[Step 1] Authenticating AICTE Officer...", flush=True)
    officer_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "officer@aicte-india.org",
        "password": "Officer@123"
    })
    assert officer_login.status_code == 200, f"Officer login failed: {officer_login.text}"
    officer_token = officer_login.json()["access_token"]
    officer_headers = {"Authorization": f"Bearer {officer_token}"}
    print("  -> Authenticated AICTE Officer successfully.", flush=True)

    # 2. Login Institution User (Apex)
    print("\n[Step 2] Authenticating Institution User (Apex)...", flush=True)
    apex_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "apex@institution.edu.in",
        "password": "Institute@123"
    })
    assert apex_login.status_code == 200, f"Apex login failed: {apex_login.text}"
    apex_token = apex_login.json()["access_token"]
    apex_headers = {"Authorization": f"Bearer {apex_token}"}
    print("  -> Authenticated Apex Institute user successfully.", flush=True)

    # 3. Login Institution User (Zenith) for isolation checks
    print("\n[Step 3] Authenticating Institution User (Zenith)...", flush=True)
    zenith_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "zenith@institution.edu.in",
        "password": "Institute@123"
    })
    assert zenith_login.status_code == 200, f"Zenith login failed: {zenith_login.text}"
    zenith_token = zenith_login.json()["access_token"]
    zenith_headers = {"Authorization": f"Bearer {zenith_token}"}
    print("  -> Authenticated Zenith University user successfully.", flush=True)

    # Fetch Apex applications
    apex_apps = requests.get(f"{BASE_URL}/applications", headers=apex_headers).json()
    assert len(apex_apps) > 0, "No applications found for Apex"
    target_app = apex_apps[0]
    app_id = target_app["id"]
    ref_no = target_app["reference_no"]
    print(f"  -> Target Application: ID={app_id}, Ref={ref_no}, Current Status={target_app['status']}", flush=True)

    # Fetch documents for document_id
    docs = requests.get(f"{BASE_URL}/applications/{app_id}/documents", headers=apex_headers).json()
    doc_id = docs[0]["id"] if len(docs) > 0 else 1

    # Count existing Apex notifications
    apex_notifs_before = requests.get(f"{BASE_URL}/notifications", headers=apex_headers).json()
    before_count = len(apex_notifs_before)

    # 4. Test Action: UNDER_REVIEW
    print("\n[Step 4] Testing 'UNDER_REVIEW' decision action...", flush=True)
    res_review = requests.post(f"{BASE_URL}/applications/{app_id}/decisions", headers=officer_headers, json={
        "decision": "UNDER_REVIEW",
        "justification": "Active preliminary scrutiny of uploaded fire and building certificates by AICTE scrutiny officer."
    })
    assert res_review.status_code == 200, f"Under review failed: {res_review.text}"
    print("  -> UNDER_REVIEW decision recorded successfully.", flush=True)

    # Verify notification delivered to Apex
    apex_notifs_after = requests.get(f"{BASE_URL}/notifications", headers=apex_headers).json()
    assert len(apex_notifs_after) > before_count, "No notification created for Apex"
    latest_notif = apex_notifs_after[0]
    assert latest_notif["action_type"] == "UNDER_REVIEW", f"Expected UNDER_REVIEW, got {latest_notif['action_type']}"
    assert f"/applications/{app_id}" in (latest_notif["link"] or ""), f"Link mismatch: {latest_notif['link']}"
    print(f"  -> Apex received notification: '{latest_notif['title']}' with link: {latest_notif['link']}", flush=True)

    # 5. Test Action: REJECT (Validation enforcement)
    print("\n[Step 5] Testing 'REJECT' decision action with validation checks...", flush=True)
    # A: Empty rejection reason must fail
    fail_rej1 = requests.post(f"{BASE_URL}/applications/{app_id}/decisions", headers=officer_headers, json={
        "decision": "REJECT",
        "justification": "This application fails mandatory criteria.",
        "rejection_reason": ""
    })
    assert fail_rej1.status_code == 400, f"Expected 400 for empty rejection reason, got {fail_rej1.status_code}"
    print("  -> Properly rejected submission with missing rejection reason (400 Bad Request).", flush=True)

    # B: Short justification must fail
    fail_rej2 = requests.post(f"{BASE_URL}/applications/{app_id}/decisions", headers=officer_headers, json={
        "decision": "REJECT",
        "rejection_reason": "Critical Safety Compliance Shortfall",
        "justification": "No"
    })
    assert fail_rej2.status_code == 400, f"Expected 400 for short justification, got {fail_rej2.status_code}"
    print("  -> Properly rejected submission with short justification (400 Bad Request).", flush=True)

    # C: Valid rejection
    success_rej = requests.post(f"{BASE_URL}/applications/{app_id}/decisions", headers=officer_headers, json={
        "decision": "REJECT",
        "rejection_reason": "Critical Safety Compliance Shortfall (Expired / Invalid Fire NOC)",
        "justification": "The uploaded fire safety certificate expired on 2024-05-10. Regulatory mandate requires a valid NOC during the academic cycle.",
        "rule_ids": [1],
        "document_ids": [doc_id]
    })
    assert success_rej.status_code == 200, f"Valid rejection failed: {success_rej.text}"
    rej_data = success_rej.json()
    assert rej_data["rejection_reason"] == "Critical Safety Compliance Shortfall (Expired / Invalid Fire NOC)"
    print("  -> Valid REJECT decision recorded and persisted with rejection_reason.", flush=True)

    # Verify Apex received REJECT notification
    apex_notifs_rej = requests.get(f"{BASE_URL}/notifications", headers=apex_headers).json()
    assert apex_notifs_rej[0]["action_type"] == "REJECT"
    assert apex_notifs_rej[0]["notification_type"] == "ERROR"
    assert "Critical Safety" in apex_notifs_rej[0]["details"]
    print("  -> Apex received official Rejection notification with full memo details.", flush=True)

    # 6. Test Institution Privacy & Isolation (Zenith must NOT see Apex notifications)
    print("\n[Step 6] Testing Confidentiality Isolation between Institutions...", flush=True)
    zenith_notifs = requests.get(f"{BASE_URL}/notifications", headers=zenith_headers).json()
    for zn in zenith_notifs:
        assert zn["application_id"] != app_id, f"SECURITY LEAK: Zenith user can see Apex application notification {zn}"
    print("  -> Verified: Zenith University received ZERO notifications belonging to Apex Institute.", flush=True)

    # 7. Test Action: REQUEST_CORRECTION
    print("\n[Step 7] Testing 'REQUEST_CORRECTION' action...", flush=True)
    res_corr = requests.post(f"{BASE_URL}/applications/{app_id}/decisions", headers=officer_headers, json={
        "decision": "REQUEST_CORRECTION",
        "justification": "Please upload a valid, certified Fire Safety NOC for 2025-2026 issued by the State Fire Services Directorate.",
        "document_ids": [doc_id]
    })
    assert res_corr.status_code == 200, f"Request correction failed: {res_corr.text}"
    print("  -> REQUEST_CORRECTION decision recorded. Application transitioned to CLARIFICATION_REQUESTED.", flush=True)

    # Verify ClarificationRequest was created
    clarifs = requests.get(f"{BASE_URL}/applications/{app_id}/clarifications", headers=apex_headers).json()
    assert len(clarifs) > 0, "No clarification request found"
    latest_clar = clarifs[0]
    assert "Correction Requested" in latest_clar["subject"]
    print(f"  -> Clarification #{latest_clar['id']} created with instructions: '{latest_clar['instructions_for_correction']}'", flush=True)

    # 8. Test Institution Correction Submission
    print("\n[Step 8] Testing Institution Correction / Resubmission Upload...", flush=True)
    fake_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Title (Corrected Fire NOC) >>\nendobj\ntrailer\n<< >>\n%%EOF"
    files = {
        "file": ("corrected_fire_noc_2026.pdf", fake_pdf_content, "application/pdf")
    }
    data = {
        "clarification_id": latest_clar["id"],
        "explanation": "Uploaded renewal receipt and certified Fire Safety NOC valid through April 2027.",
        "document_id": doc_id
    }

    submit_res = requests.post(
        f"{BASE_URL}/clarifications/{latest_clar['id']}/correction",
        headers=apex_headers,
        data=data,
        files=files
    )
    assert submit_res.status_code == 200, f"Submit correction failed: {submit_res.text}"
    print("  -> Correction submitted successfully. Application status:", submit_res.json()["application_status"], flush=True)

    # Verify officer received notification of correction submission
    officer_notifs = requests.get(f"{BASE_URL}/notifications", headers=officer_headers).json()
    corr_notifs = [n for n in officer_notifs if n.get("action_type") == "CORRECTION_SUBMITTED"]
    assert len(corr_notifs) > 0, "AICTE officer did not receive correction submission notification"
    print(f"  -> Officer received notification: '{corr_notifs[0]['title']}' - '{corr_notifs[0]['message']}'", flush=True)

    # 9. Test Action: APPROVE
    print("\n[Step 9] Testing 'APPROVE' decision action...", flush=True)
    res_appr = requests.post(f"{BASE_URL}/applications/{app_id}/decisions", headers=officer_headers, json={
        "decision": "APPROVE",
        "justification": "All requirements verified. Corrected Fire NOC accepted. Approved for Academic Year 2025-2026.",
        "is_override": True,
        "override_reason": "Officer verified temporary clearance permit pending final state gazette."
    })
    assert res_appr.status_code == 200, f"Approve failed: {res_appr.text}"
    print("  -> Application successfully APPROVED.", flush=True)

    # Verify Apex received approval notification
    apex_notifs_appr = requests.get(f"{BASE_URL}/notifications", headers=apex_headers).json()
    assert apex_notifs_appr[0]["action_type"] == "APPROVE"
    assert apex_notifs_appr[0]["notification_type"] == "SUCCESS"
    print(f"  -> Apex received approval notification: '{apex_notifs_appr[0]['title']}'", flush=True)

    # 10. Test Decisions History Retrieval
    print("\n[Step 10] Testing GET /applications/{id}/decisions audit history...", flush=True)
    dec_history = requests.get(f"{BASE_URL}/applications/{app_id}/decisions", headers=officer_headers).json()
    assert len(dec_history) >= 4, f"Expected at least 4 decisions, got {len(dec_history)}"
    print(f"  -> Successfully fetched {len(dec_history)} immutable regulatory decision audit records:", flush=True)
    for d in dec_history[:4]:
        print(f"     * [{d['decision']}] By: {d['officer_name']} at {d['decided_at']}. Reason: {d.get('rejection_reason') or 'N/A'}", flush=True)

    print("\n==================================================", flush=True)
    print("ALL REGULENS APPROVAL & NOTIFICATION TESTS PASSED!", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    run_tests()
