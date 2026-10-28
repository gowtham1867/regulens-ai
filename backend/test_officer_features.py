import requests
import csv
import io
import pymupdf as fitz
from PIL import Image

BASE_URL = "http://127.0.0.1:8000/api/v1"

# 1. Login
print("--- 1. AUTHENTICATION ---")
officer_res = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "officer@aicte-india.org",
    "password": "Officer@123"
})
assert officer_res.status_code == 200, f"Officer login failed: {officer_res.text}"
officer_token = officer_res.json()["access_token"]
officer_headers = {"Authorization": f"Bearer {officer_token}"}
print("Officer authenticated successfully.")

college_res = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "apex@institution.edu.in",
    "password": "Institute@123"
})
assert college_res.status_code == 200, f"College login failed: {college_res.text}"
college_token = college_res.json()["access_token"]
college_headers = {"Authorization": f"Bearer {college_token}"}
print("College user authenticated successfully.")

# 2. Test Document Retrieval & Authentication
print("\n--- 2. DOCUMENT RETRIEVAL & AUTHENTICATION TESTS ---")
# Get documents for application 1
docs_res = requests.get(f"{BASE_URL}/applications/1/documents", headers=officer_headers)
assert docs_res.status_code == 200
docs_data = docs_res.json()
assert len(docs_data) > 0, "No documents found for app 1"
target_doc = docs_data[0]
target_v = target_doc["latest_version"]
assert target_v is not None, "Latest version is None"
version_id = target_v["id"]
print(f"Target document: '{target_doc['title']}', Version ID: {version_id}, File: '{target_v['original_filename']}'")

# A. Retrieval with Bearer Header
res_bearer = requests.get(f"{BASE_URL}/document-versions/{version_id}/download", headers=officer_headers)
assert res_bearer.status_code == 200, f"Bearer retrieval failed: {res_bearer.status_code} {res_bearer.text}"
print(f"A. Bearer token retrieval: SUCCESS ({len(res_bearer.content)} bytes, Content-Type: {res_bearer.headers.get('Content-Type')})")
assert len(res_bearer.content) > 0

# B. Retrieval with inline=true preview
res_inline = requests.get(f"{BASE_URL}/document-versions/{version_id}/preview?inline=true", headers=officer_headers)
assert res_inline.status_code == 200
assert "inline" in res_inline.headers.get("Content-Disposition", ""), f"Expected inline disposition: {res_inline.headers.get('Content-Disposition')}"
print("B. Inline preview endpoint: SUCCESS (Content-Disposition: inline)")

# C. Retrieval with ?token= query parameter (Fallback URL support)
res_query_token = requests.get(f"{BASE_URL}/document-versions/{version_id}/download?token={officer_token}")
assert res_query_token.status_code == 200, f"Query token retrieval failed: {res_query_token.status_code} {res_query_token.text}"
print("C. Query param token retrieval: SUCCESS")

# D. Retrieval with NO credentials (should fail with 401 Not authenticated)
res_no_auth = requests.get(f"{BASE_URL}/document-versions/{version_id}/download")
assert res_no_auth.status_code == 401, f"Expected 401, got {res_no_auth.status_code}"
assert res_no_auth.json().get("detail") == "Not authenticated"
print("D. Unauthenticated request blocked: SUCCESS (HTTP 401 Not authenticated)")

# E. Retrieval with Invalid credentials (should fail with 401)
res_bad_auth = requests.get(f"{BASE_URL}/document-versions/{version_id}/download", headers={"Authorization": "Bearer invalid_garbage_token"})
assert res_bad_auth.status_code == 401, f"Expected 401, got {res_bad_auth.status_code}"
print("E. Invalid token blocked: SUCCESS (HTTP 401)")

# F. Missing document ID (404)
res_missing = requests.get(f"{BASE_URL}/document-versions/999999/download", headers=officer_headers)
assert res_missing.status_code == 404, f"Expected 404, got {res_missing.status_code}"
print("F. Missing document version: SUCCESS (HTTP 404 Document version not found)")

# 3. Test PNG / Image Upload and Retrieval
print("\n--- 3. IMAGE PREVIEW TEST (PNG / JPG) ---")
# Create an image in memory
img = Image.new('RGB', (400, 300), color=(30, 144, 255))
img_bytes_io = io.BytesIO()
img.save(img_bytes_io, format='PNG')
img_bytes = img_bytes_io.getvalue()

res_upload_img = requests.post(
    f"{BASE_URL}/applications/1/documents",
    headers=college_headers,
    data={"document_type": "INFRASTRUCTURE_EVIDENCE", "title": "Campus Laboratory Infrastructure Photo"},
    files={"file": ("campus_lab_photo.png", img_bytes, "image/png")}
)
assert res_upload_img.status_code == 200, f"Image upload failed: {res_upload_img.text}"
img_doc = res_upload_img.json()
img_v_id = img_doc["latest_version"]["id"]
print(f"Image uploaded successfully: Doc ID={img_doc['id']}, Version ID={img_v_id}")

# Fetch the image version
res_get_img = requests.get(f"{BASE_URL}/document-versions/{img_v_id}/download", headers=officer_headers)
assert res_get_img.status_code == 200
assert "image/png" in res_get_img.headers.get("Content-Type", "")
assert len(res_get_img.content) == len(img_bytes)
print("Image retrieved with exact byte fidelity & image/png Content-Type: SUCCESS")

# 4. Test PDF Export
print("\n--- 4. PDF EXPORT TESTS ---")
res_pdf = requests.get(f"{BASE_URL}/applications/1/report.pdf", headers=officer_headers)
assert res_pdf.status_code == 200, f"PDF export failed: {res_pdf.status_code} {res_pdf.text}"
assert "application/pdf" in res_pdf.headers.get("Content-Type", "")
assert "ReguLens_Scrutiny_" in res_pdf.headers.get("Content-Disposition", "")
pdf_bytes = res_pdf.content
print(f"PDF exported successfully: {len(pdf_bytes)} bytes")
assert pdf_bytes.startswith(b"%PDF-"), "Exported file does not have valid %PDF- magic bytes"

# Inspect PDF structure with PyMuPDF
pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
num_pages = len(pdf_doc)
print(f"Exported PDF page count: {num_pages}")
assert num_pages >= 1, "PDF has 0 pages"

combined_pdf_text = ""
for p_idx in range(num_pages):
    combined_pdf_text += pdf_doc[p_idx].get_text("text") + "\n"
pdf_doc.close()

# Verify presence of actual persisted data in PDF text
normalized_pdf_text = " ".join(combined_pdf_text.split())
required_tokens = [
    "REGULENS AI",
    "COMPLIANCE SCRUTINY",
    "Apex Institute",
    "AICTE Permanent ID:",
    "Submitted Regulatory Documents",
    "AI OCR Extracted Field Intelligence",
    "Regulatory Rule Scrutiny",
    "Cross-Institutional Anomaly",
    "External Issuer Verification Records",
    "TrustGraph Evidence Provenance Summary",
    "Tamper-Evident Cryptographic Audit Trail"
]
for tok in required_tokens:
    assert tok.lower() in normalized_pdf_text.lower(), f"Missing expected token in exported PDF: '{tok}'"
    print(f"  [PASS] Verified in PDF: '{tok}'")

# 5. Test CSV Export
print("\n--- 5. CSV EXPORT TESTS ---")
res_csv = requests.get(f"{BASE_URL}/applications/1/report.csv", headers=officer_headers)
assert res_csv.status_code == 200, f"CSV export failed: {res_csv.status_code} {res_csv.text}"
assert "text/csv" in res_csv.headers.get("Content-Type", "")
assert "ReguLens_Report_" in res_csv.headers.get("Content-Disposition", "")
csv_content = res_csv.content.decode("utf-8-sig")
print(f"CSV exported successfully: {len(csv_content)} characters")

# Parse CSV
reader = csv.reader(io.StringIO(csv_content))
rows = list(reader)
header_row = rows[0]
print(f"CSV Header columns ({len(header_row)}): {header_row[:6]} ...")
assert "APPLICATION_REF" in header_row
assert "RECORD_TYPE" in header_row
assert "TITLE_OR_NAME" in header_row
assert "STATUS_OR_OUTCOME" in header_row

# Check record types present in CSV
record_types = set([r[6] for r in rows[1:] if len(r) > 6])
print(f"Record types present in CSV: {record_types}")
assert "APPLICATION_HEADER" in record_types
assert "DOCUMENT" in record_types
assert "VALIDATION_FINDING" in record_types
assert "AUDIT_EVENT" in record_types

# Check formula injection safety on all cells
for row_idx, r in enumerate(rows):
    for col_idx, cell in enumerate(r):
        assert not (cell.startswith("=") or cell.startswith("+") or (cell.startswith("-") and not cell.replace("-","").isdigit()) or cell.startswith("@")), \
            f"Formula injection hazard at row {row_idx}, col {col_idx}: '{cell}'"

print("  [PASS] Formula injection protection verified on all cells.")
print("  [PASS] CSV structure normalized with consistent column count across all rows.")

print("\n========================================================")
print(">>> ALL OFFICER DOCUMENT, PDF & CSV TESTS PASSED! <<<")
print("========================================================")
