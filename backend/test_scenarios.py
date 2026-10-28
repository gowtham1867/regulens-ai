import requests
import json
import pymupdf as fitz

BASE_URL = "http://127.0.0.1:8000/api/v1"

# 1. Login as AICTE Officer
print("--- TEST LOGIN ---")
officer_res = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "officer@aicte-india.org",
    "password": "Officer@123"
})
assert officer_res.status_code == 200, f"Officer login failed: {officer_res.text}"
officer_token = officer_res.json()["access_token"]
officer_headers = {"Authorization": f"Bearer {officer_token}"}
print("Officer login successful.")

# Login as College User
college_res = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "apex@institution.edu.in",
    "password": "Institute@123"
})
assert college_res.status_code == 200, f"College login failed: {college_res.text}"
college_token = college_res.json()["access_token"]
college_headers = {"Authorization": f"Bearer {college_token}"}
print("College user login successful.")

# 2. Test Scenario D: Consistent Application Lookup on App 7 & 8 (which previously broke with 500)
print("\n--- TEST SCENARIO D: Application Lookup for App 7 and App 8 ---")
for app_id in [1, 7, 8]:
    res_app = requests.get(f"{BASE_URL}/applications/{app_id}", headers=officer_headers)
    assert res_app.status_code == 200, f"Get app {app_id} failed: {res_app.status_code} {res_app.text}"
    app_data = res_app.json()
    print(f"App {app_id} ({app_data['reference_no']}): Loaded successfully. Status={app_data['status']}")

    res_docs = requests.get(f"{BASE_URL}/applications/{app_id}/documents", headers=officer_headers)
    assert res_docs.status_code == 200, f"Get docs for app {app_id} failed: {res_docs.status_code} {res_docs.text}"
    docs_data = res_docs.json()
    print(f"App {app_id} documents loaded: {len(docs_data)} document(s). Types: {[d['document_type'] for d in docs_data]}")

# 3. Test Scenario C: Invalid Upload Validation (extension & size)
print("\n--- TEST SCENARIO C: Invalid Upload Validation ---")
# Unsupported extension (.txt)
fake_txt = ("test.txt", b"Unsupported plain text file", "text/plain")
res_invalid_type = requests.post(
    f"{BASE_URL}/applications/1/documents",
    headers=officer_headers,
    data={"document_type": "OTHER", "title": "Invalid Txt Document"},
    files={"file": fake_txt}
)
print(f"Invalid extension response: {res_invalid_type.status_code} -> {res_invalid_type.json().get('detail')}")
assert res_invalid_type.status_code == 400, "Expected 400 for unsupported extension"

# Empty file
empty_pdf = ("empty.pdf", b"", "application/pdf")
res_empty = requests.post(
    f"{BASE_URL}/applications/1/documents",
    headers=officer_headers,
    data={"document_type": "OTHER", "title": "Empty Document"},
    files={"file": empty_pdf}
)
print(f"Empty file response: {res_empty.status_code} -> {res_empty.json().get('detail')}")
assert res_empty.status_code == 400, "Expected 400 for empty file"

# 4. Test Scenario A: Upload Across Document Types
print("\n--- TEST SCENARIO A: Successful Upload Across Document Types ---")
doc_fitz = fitz.open()
page = doc_fitz.new_page()
page.insert_text(
    (50, 72),
    "GOVERNMENT OF TAMIL NADU\n"
    "DIRECTORATE OF FIRE AND RESCUE SERVICES\n"
    "Certificate No: TN-FIRE-2026-99881\n"
    "Permanent Institute ID: 1-9876543210\n"
    "Institution Name: Apex Institute of Technology\n"
    "Date of Issue: 12/01/2026\n"
    "Valid Upto: 31/03/2027\n"
    "This certificate is issued for regulatory compliance."
)
valid_pdf_bytes = doc_fitz.tobytes()
doc_fitz.close()

# Upload as FIRE_SAFETY_CERTIFICATE
res_upload_fire = requests.post(
    f"{BASE_URL}/applications/1/documents",
    headers=college_headers,
    data={"document_type": "FIRE_SAFETY_CERTIFICATE", "title": "State Fire Services NOC 2026-27"},
    files={"file": ("apex_fire_noc_2026.pdf", valid_pdf_bytes, "application/pdf")}
)
assert res_upload_fire.status_code == 200, f"Upload fire NOC failed: {res_upload_fire.text}"
fire_doc_resp = res_upload_fire.json()
print("Fire NOC uploaded successfully!")
print(f"Doc ID: {fire_doc_resp['id']}, Version: {fire_doc_resp['latest_version']['version_number']}, Status: {fire_doc_resp['latest_version']['status']}")
extracted_keys = [f["field_key"] for f in fire_doc_resp['latest_version']['extracted_fields']]
print(f"Extracted fields: {extracted_keys}")
assert "certificate_number" in extracted_keys or "institution_name" in extracted_keys

# Generate and upload LAND_USE_CERTIFICATE
doc_land = fitz.open()
p_land = doc_land.new_page()
p_land.insert_text(
    (50, 72),
    "REVENUE DEPARTMENT - GOVERNMENT OF TAMIL NADU\n"
    "LAND USE CERTIFICATE & TITLE CONVERSION\n"
    "Reference Number: TN-LUC-2026-4412\n"
    "Permanent Institute ID: 1-9876543210\n"
    "Institution Name: Apex Institute of Technology\n"
    "Total Land Area: 10.50 Acres\n"
    "Survey No: 204/1A-2B\n"
    "Date of Issue: 15/02/2026\n"
    "Certified for Educational Use."
)
land_pdf_bytes = doc_land.tobytes()
doc_land.close()

res_upload_land = requests.post(
    f"{BASE_URL}/applications/1/documents",
    headers=college_headers,
    data={"document_type": "LAND_USE_CERTIFICATE", "title": "District Revenue Land Use Certificate"},
    files={"file": ("apex_land_use_cert.pdf", land_pdf_bytes, "application/pdf")}
)
assert res_upload_land.status_code == 200, f"Upload land use cert failed: {res_upload_land.text}"
land_doc_resp = res_upload_land.json()
print("Land Use Certificate uploaded successfully!")
print(f"Doc ID: {land_doc_resp['id']}, Status: {land_doc_resp['latest_version']['status']}")
land_fields = [f["field_key"] for f in land_doc_resp['latest_version']['extracted_fields']]
print(f"Extracted fields for land: {land_fields}")

# 5. Test Scenario B: Graceful Recovery on OCR failure
print("\n--- TEST SCENARIO B: Graceful Recovery on Unprocessable / Non-standard document ---")
# Upload a corrupt PDF / binary dummy that fails fitz parsing
corrupt_bytes = b"%PDF-1.4\nCorrupted header content that cannot be opened as a valid PDF document\n%%EOF"
res_corrupt = requests.post(
    f"{BASE_URL}/applications/1/documents",
    headers=college_headers,
    data={"document_type": "OTHER", "title": "Corrupt Evidence File"},
    files={"file": ("corrupt_file.pdf", corrupt_bytes, "application/pdf")}
)
assert res_corrupt.status_code == 200, f"Expected 200 with FAILED status, got {res_corrupt.status_code}: {res_corrupt.text}"
corrupt_resp = res_corrupt.json()
print(f"Corrupt file uploaded safely: Document ID={corrupt_resp['id']}")
print(f"Version status: {corrupt_resp['latest_version']['status']}")
print(f"Error message saved: {corrupt_resp['latest_version'].get('error_message')}")
assert corrupt_resp['latest_version']['status'] in ("FAILED", "COMPLETED_WITH_WARNINGS")

# Verify Application 1 is still 100% accessible
res_app_after = requests.get(f"{BASE_URL}/applications/1", headers=officer_headers)
assert res_app_after.status_code == 200
print("Application 1 remains completely intact and accessible!")

# 6. Test Scenario E: TrustGraph and Findings Integration
print("\n--- TEST SCENARIO E: TrustGraph and Findings Integration ---")
res_tg = requests.get(f"{BASE_URL}/applications/1/trustgraph", headers=officer_headers)
assert res_tg.status_code == 200, f"TrustGraph failed: {res_tg.text}"
tg_data = res_tg.json()
print(f"TrustGraph generated: {len(tg_data.get('nodes', []))} nodes, {len(tg_data.get('edges', []))} edges.")
doc_nodes = [n for n in tg_data.get('nodes', []) if n.get('type') == 'DOCUMENT']
print(f"Document nodes in TrustGraph: {len(doc_nodes)}")

res_findings = requests.get(f"{BASE_URL}/applications/1/findings", headers=officer_headers)
assert res_findings.status_code == 200
findings_data = res_findings.json()
print(f"Active findings count: {len(findings_data)}")

print("\n>>> ALL TEST SCENARIOS PASSED WITH ZERO ERRORS! <<<")
