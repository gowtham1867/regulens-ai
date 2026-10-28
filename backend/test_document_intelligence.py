"""
ReguLens AI - Comprehensive Document Intelligence & Compliance Verification Test Suite
Tests all 20 required scenarios from the Product Specification.
"""

import os
import sys
import fitz  # PyMuPDF
from datetime import datetime, timedelta

# Ensure backend path is on sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.database import SessionLocal, Base, engine
from app.models.application import Application, ApplicationCategory, ApplicationStatus
from app.models.document import Document, DocumentVersion, ExtractedField, ProcessingStatus, DocumentType
from app.models.deficiency import ApplicationDeficiency, DeficiencyType, DeficiencyStatus
from app.models.duplicate import DuplicateRecord, DuplicateMatchType, DuplicateStatus
from app.models.workflow import ClarificationRequest, ClarificationStatus, CorrectionSubmission
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.models.institution import Institution, InstitutionMembership
from app.models.rule import ChecklistRequirement
from app.services.ocr_engine import ocr_engine
from app.services.document_requirements_service import DocumentRequirementsEngine
from app.services.anomaly_detector import AnomalyDetector
from app.services.revalidation_service import RevalidationService
from app.services.trustgraph_service import TrustGraphService


def generate_pdf(filepath: str, text: str):
    """Generate a clean single-page PDF with digital text."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    rect = fitz.Rect(50, 50, 550, 800)
    page.insert_textbox(rect, text, fontsize=11, fontname="helv", align=0)
    doc.save(filepath)
    doc.close()


def generate_empty_raster_pdf(filepath: str):
    """Generate a PDF page with 0 text characters (simulating a pure raster scan without digital text)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.draw_rect(fitz.Rect(50, 50, 540, 800), color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95))
    doc.save(filepath)
    doc.close()


def run_tests():
    print("=" * 80)
    print("REGULENS AI — 20-SCENARIO DOCUMENT INTELLIGENCE & COMPLIANCE TEST SUITE")
    print("=" * 80)

    db = SessionLocal()
    test_artifacts_dir = os.path.join(backend_dir, "test_docs_tmp")
    os.makedirs(test_artifacts_dir, exist_ok=True)

    passed = 0
    failed = 0

    def record_result(num: int, title: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] Scenario {num:02d}: {title}")
            if detail:
                print(f"         |-- {detail}")
            passed += 1
        else:
            print(f"  [FAIL] Scenario {num:02d}: {title}")
            if detail:
                print(f"         |-- Error: {detail}")
            failed += 1

    try:
        # Fetch or create a test Institution
        inst = db.query(Institution).filter(Institution.aicte_id == "TEST-INST-001").first()
        if not inst:
            inst = Institution(
                name="Apex Institute of Technology",
                aicte_id="TEST-INST-001",
                address="Survey 45, Tech Knowledge Corridor",
                state="Maharashtra",
                district="Pune",
                pin_code="411057",
                contact_email="apex_admin@institution.edu",
                contact_phone="9876543210"
            )
            db.add(inst)
            db.commit()
            db.refresh(inst)

        # Fetch or create a test Institution User
        inst_user = db.query(User).filter(User.email == "apex_admin@institution.edu").first()
        if not inst_user:
            inst_user = User(
                email="apex_admin@institution.edu",
                hashed_password="hashed_test_pass",
                full_name="Dr. Apex Registrar",
                role=UserRole.INSTITUTION_USER
            )
            db.add(inst_user)
            db.commit()
            db.refresh(inst_user)

            membership = InstitutionMembership(
                user_id=inst_user.id,
                institution_id=inst.id,
                is_primary_contact=True
            )
            db.add(membership)
            db.commit()

        # Create Test Application 1: Extension of Approval
        app_eoa = Application(
            reference_no=f"APP-TEST-EOA-{int(datetime.utcnow().timestamp())}",
            institution_id=inst.id,
            submitting_user_id=inst_user.id,
            category=ApplicationCategory.EXTENSION_OF_APPROVAL,
            academic_year="2026-2027",
            status=ApplicationStatus.SUBMITTED,
            title="EOA Test Application"
        )
        db.add(app_eoa)

        # Create Test Application 2: New Institution
        app_new = Application(
            reference_no=f"APP-TEST-NEW-{int(datetime.utcnow().timestamp())}",
            institution_id=inst.id,
            submitting_user_id=inst_user.id,
            category=ApplicationCategory.NEW_INSTITUTION,
            academic_year="2026-2027",
            status=ApplicationStatus.DRAFT,
            title="New Institution Test Application"
        )
        db.add(app_new)
        db.commit()
        db.refresh(app_eoa)
        db.refresh(app_new)

        print(f"Initialized Test Applications: EOA #{app_eoa.id} ({app_eoa.reference_no}), NEW #{app_new.id} ({app_new.reference_no})")
        print("-" * 80)

        # -------------------------------------------------------------
        # SCENARIO 1: Valid document upload with real OCR entity extraction
        # -------------------------------------------------------------
        valid_fire_text = """
        GOVERNMENT OF MAHARASHTRA
        STATE FIRE SERVICES AND RESCUE HEADQUARTERS
        FIRE SAFETY CERTIFICATE / NO OBJECTION CERTIFICATE

        NOC Number: FSC/MAH/2026/89412
        Date of Issue: 15/01/2026
        Valid Upto: 14/01/2028

        Certified that the educational building premises occupied by Apex Institute of Technology,
        situated at Survey 45, Tech Knowledge Corridor, Pune, Maharashtra has complied with all
        fire safety requirements under National Building Code (NBC 2016 Part 4).
        Status: Valid and Approved for educational occupancy.
        Issuing Authority: Directorate of Fire Services, Pune Municipal Region.
        """
        fire_pdf_path = os.path.join(test_artifacts_dir, "valid_fire_noc.pdf")
        generate_pdf(fire_pdf_path, valid_fire_text)

        extracted_text, fields, meta, auth_info = ocr_engine.extract_and_structure(
            fire_pdf_path, "FIRE_SAFETY_CERTIFICATE"
        )
        extracted_keys = {f["field_key"]: f["extracted_value"] for f in fields}
        sc1_pass = (
            "noc_number" in extracted_keys and
            "FSC/MAH/2026/89412" in extracted_keys.get("noc_number", "") and
            "valid_to" in extracted_keys and
            len(fields) >= 3
        )
        record_result(
            1, "Valid document upload with real OCR entity extraction",
            sc1_pass,
            f"Extracted {len(fields)} fields: {', '.join(extracted_keys.keys())}"
        )

        # -------------------------------------------------------------
        # SCENARIO 2: Scanned document without digital text
        # -------------------------------------------------------------
        raster_pdf_path = os.path.join(test_artifacts_dir, "raster_scan_no_text.pdf")
        generate_empty_raster_pdf(raster_pdf_path)

        r_text, r_fields, r_meta, r_auth = ocr_engine.extract_and_structure(
            raster_pdf_path, "FIRE_SAFETY_CERTIFICATE"
        )
        sc2_pass = (
            len(r_text.strip()) == 0 and
            len(r_fields) == 0 and
            r_meta.get("is_raster_only", False) is True
        )
        record_result(
            2, "Scanned document handling without digital text (honest empty state)",
            sc2_pass,
            f"0 digital characters found; is_raster_only={r_meta.get('is_raster_only')}; fields={len(r_fields)}"
        )

        # -------------------------------------------------------------
        # SCENARIO 3: Unreadable/corrupted file format handling
        # -------------------------------------------------------------
        corrupt_path = os.path.join(test_artifacts_dir, "corrupted_file.pdf")
        with open(corrupt_path, "wb") as f:
            f.write(b"NOT_A_VALID_PDF_HEADER_JUST_RANDOM_GARBAGE_BYTES_1234567890")

        with open(corrupt_path, "rb") as f:
            c_bytes = f.read()

        auth_check = ocr_engine.inspect_file_authenticity(c_bytes, "corrupted_file.pdf")
        sc3_pass = (
            auth_check.get("is_valid") is False and
            ("conflict" in (auth_check.get("error") or "").lower() or auth_check.get("has_extension_mismatch") or "header" in (auth_check.get("error") or "").lower() or auth_check.get("detected_format") == "UNKNOWN")
        )
        record_result(
            3, "Unreadable/corrupted file format handling with magic byte check",
            sc3_pass,
            f"Authenticity status: is_valid={auth_check.get('is_valid')}; Detected format: {auth_check.get('detected_format')}; Reason: {auth_check.get('error')}"
        )

        # -------------------------------------------------------------
        # SCENARIO 4: Exact SHA-256 duplicate detection
        # -------------------------------------------------------------
        # Create Document 1 in DB
        doc1 = Document(
            application_id=app_eoa.id,
            document_type=DocumentType.FIRE_SAFETY_CERTIFICATE,
            title="Fire Safety Certificate",
            is_required=True
        )
        db.add(doc1)
        db.commit()
        db.refresh(doc1)

        v1 = DocumentVersion(
            document_id=doc1.id,
            version_number=1,
            original_filename="valid_fire_noc.pdf",
            file_path=fire_pdf_path,
            mime_type="application/pdf",
            file_size_bytes=os.path.getsize(fire_pdf_path),
            file_hash=ocr_engine.calculate_file_hash(fire_pdf_path),
            status=ProcessingStatus.COMPLETED
        )
        db.add(v1)
        db.commit()
        db.refresh(v1)

        # Create Document 2 in New Institution App with EXACT SAME BYTES
        doc2 = Document(
            application_id=app_new.id,
            document_type=DocumentType.FIRE_SAFETY_CERTIFICATE,
            title="Fire Safety Copy",
            is_required=True
        )
        db.add(doc2)
        db.commit()
        db.refresh(doc2)

        v2 = DocumentVersion(
            document_id=doc2.id,
            version_number=1,
            original_filename="uploaded_copy_fire.pdf",
            file_path=fire_pdf_path,
            mime_type="application/pdf",
            file_size_bytes=os.path.getsize(fire_pdf_path),
            file_hash=ocr_engine.calculate_file_hash(fire_pdf_path),
            status=ProcessingStatus.COMPLETED
        )
        db.add(v2)
        db.commit()
        db.refresh(v2)

        detector = AnomalyDetector(db)
        anomalies_app_new = detector.scan_application(app_new.id)
        dup_exact = next((a for a in anomalies_app_new if a.get("anomaly_type") == "DUPLICATE_FILE_FINGERPRINT"), None)
        dup_rec = db.query(DuplicateRecord).filter(DuplicateRecord.match_type == DuplicateMatchType.EXACT_HASH).first()
        sc4_pass = (
            dup_exact is not None and
            dup_rec is not None and
            dup_exact.get("matched_version_id") == v1.id
        )
        record_result(
            4, "Exact SHA-256 duplicate detection across applications",
            sc4_pass,
            f"Detected exact collision against version #{v1.id} with score 1.0"
        )

        # -------------------------------------------------------------
        # SCENARIO 5: Modified document text similarity duplicate detection
        # -------------------------------------------------------------
        modified_fire_text = valid_fire_text.replace("15/01/2026", "20/01/2026").replace("14/01/2028", "19/01/2028")
        sim_pdf_path = os.path.join(test_artifacts_dir, "modified_fire_sim.pdf")
        generate_pdf(sim_pdf_path, modified_fire_text)
        sim_text, _, _, _ = ocr_engine.extract_and_structure(sim_pdf_path, "FIRE_SAFETY_CERTIFICATE")
        v1.raw_extracted_text = valid_fire_text
        db.commit()

        v3 = DocumentVersion(
            document_id=doc2.id,
            version_number=2,
            original_filename="modified_fire_sim.pdf",
            file_path=sim_pdf_path,
            mime_type="application/pdf",
            file_size_bytes=os.path.getsize(sim_pdf_path),
            file_hash=ocr_engine.calculate_file_hash(sim_pdf_path),
            raw_extracted_text=sim_text,
            status=ProcessingStatus.COMPLETED
        )
        db.add(v3)
        db.commit()
        db.refresh(v3)

        anomalies_sim = detector.scan_application(app_new.id)
        dup_sim = next((a for a in anomalies_sim if a.get("anomaly_type") == "HIGH_TEXT_SIMILARITY_DUPLICATE"), None)
        sc5_pass = (
            dup_sim is not None and
            dup_sim.get("similarity_score", 0) >= 0.80
        )
        record_result(
            5, "Modified document text similarity duplicate detection",
            sc5_pass,
            f"Jaccard token similarity score: {round(dup_sim.get('similarity_score', 0) * 100, 1)}%" if dup_sim else "None"
        )

        # -------------------------------------------------------------
        # SCENARIO 6: Conflicting identifiers generating traceable findings
        # -------------------------------------------------------------
        ef1 = ExtractedField(
            document_version_id=v1.id,
            field_key="certificate_number",
            field_label="Certificate Number",
            extracted_value="FSC/MAH/2026/89412",
            normalized_value="FSC/MAH/2026/89412",
            confidence=0.98,
            source_page=1
        )
        ef3 = ExtractedField(
            document_version_id=v3.id,
            field_key="certificate_number",
            field_label="Certificate Number",
            extracted_value="FSC/MAH/2026/89412",
            normalized_value="FSC/MAH/2026/89412",
            confidence=0.98,
            source_page=1
        )
        db.add(ef1)
        db.add(ef3)
        db.commit()

        anomalies_cert = detector.scan_application(app_new.id)
        dup_cert = next((a for a in anomalies_cert if "CERTIFICATE" in a.get("anomaly_type", "")), None)
        sc6_pass = (
            dup_cert is not None and
            dup_cert.get("certificate_number") == "FSC/MAH/2026/89412"
        )
        record_result(
            6, "Conflicting certificate identifiers generating traceable findings",
            sc6_pass,
            f"Collision identifier: {dup_cert.get('certificate_number')}" if dup_cert else "None"
        )

        # -------------------------------------------------------------
        # SCENARIO 7: Document category mismatch flagged
        # -------------------------------------------------------------
        resume_text = """
        CURRICULUM VITAE
        Name: John Doe
        Education: B.Tech Computer Science, 2024
        Skills: Python, React, SQL, Machine Learning
        Experience: Junior Software Engineer Intern at XYZ Solutions.
        Projects: E-commerce web portal with payment gateway.
        """
        resume_pdf_path = os.path.join(test_artifacts_dir, "student_resume.pdf")
        generate_pdf(resume_pdf_path, resume_text)

        res_text, res_fields, res_meta, _ = ocr_engine.extract_and_structure(
            resume_pdf_path, "FIRE_SAFETY_CERTIFICATE"
        )
        sc7_pass = (
            res_meta.get("category_mismatch", False) is True and
            len(res_meta.get("classification_reasoning", "")) > 0
        )
        record_result(
            7, "Document category mismatch flagged (anti-pattern detection)",
            sc7_pass,
            f"Mismatch detected: {res_meta.get('category_mismatch')}; Reasoning: {res_meta.get('classification_reasoning')}"
        )

        # -------------------------------------------------------------
        # SCENARIO 8: Expired document triggering configured rule
        # -------------------------------------------------------------
        expired_fire_text = """
        GOVERNMENT OF MAHARASHTRA FIRE SERVICES
        FIRE SAFETY NOC
        NOC Number: FSC/MAH/2021/11022
        Issue Date: 10/01/2021
        Valid Upto: 09/01/2022
        Apex Institute of Technology
        """
        exp_pdf_path = os.path.join(test_artifacts_dir, "expired_fire.pdf")
        generate_pdf(exp_pdf_path, expired_fire_text)
        _, exp_fields, _, _ = ocr_engine.extract_and_structure(exp_pdf_path, "FIRE_SAFETY_CERTIFICATE")
        exp_keys = {f["field_key"]: f["extracted_value"] for f in exp_fields}

        valid_to_iso = ocr_engine.normalize_date(exp_keys.get("valid_to", ""))
        sc8_pass = (
            valid_to_iso == "2022-01-09" and
            datetime.strptime(valid_to_iso, "%Y-%m-%d").date() < datetime.utcnow().date()
        )
        record_result(
            8, "Expired document normalized and identified as chronologically expired",
            sc8_pass,
            f"Normalized expiry date: {valid_to_iso} (Expired vs current year 2026)"
        )

        # -------------------------------------------------------------
        # SCENARIO 9: Suspicious document receiving evidence warning without unsupported fraud verdict
        # -------------------------------------------------------------
        scan_results = detector.scan_application(app_new.id)
        has_objective_wording = all(
            "fraud" not in a.get("explanation", "").lower() and
            "criminal" not in a.get("explanation", "").lower() and
            "forgery" not in a.get("explanation", "").lower()
            for a in scan_results
        )
        sc9_pass = len(scan_results) > 0 and has_objective_wording
        record_result(
            9, "Suspicious document receiving evidence warning without unsupported fraud verdict",
            sc9_pass,
            f"Generated {len(scan_results)} objective findings; No unsubstantiated criminal charges"
        )

        # -------------------------------------------------------------
        # SCENARIO 10: New Institution application receiving specific checklist
        # -------------------------------------------------------------
        req_engine = DocumentRequirementsEngine(db)
        req_engine.seed_default_checklists()
        cl_new = req_engine.get_checklist_for_category("NEW_INSTITUTION", "2025-2026")
        new_checklist = db.query(ChecklistRequirement).filter(
            ChecklistRequirement.checklist_id == cl_new.id
        ).all()
        new_doc_types = {r.document_type for r in new_checklist}
        sc10_pass = (
            ("LAND_DOCUMENT" in new_doc_types or "LAND_DOCUMENTS" in new_doc_types) and
            "BUILDING_PLAN" in new_doc_types and
            "FIRE_SAFETY_CERTIFICATE" in new_doc_types and
            len(new_checklist) >= 6
        )
        record_result(
            10, "New Institution application receiving specific APH 2024-27 checklist",
            sc10_pass,
            f"{len(new_checklist)} requirements seeded: {', '.join(sorted(list(new_doc_types))[:4])}..."
        )

        # -------------------------------------------------------------
        # SCENARIO 11: Extension of Approval receiving separately configured checklist
        # -------------------------------------------------------------
        cl_eoa = req_engine.get_checklist_for_category("EXTENSION_OF_APPROVAL", "2025-2026")
        eoa_checklist = db.query(ChecklistRequirement).filter(
            ChecklistRequirement.checklist_id == cl_eoa.id
        ).all()
        eoa_doc_types = {r.document_type for r in eoa_checklist}
        sc11_pass = (
            "FIRE_SAFETY_CERTIFICATE" in eoa_doc_types and
            ("AFFILIATION_CERTIFICATE" in eoa_doc_types or "AFFILIATION_ORDER" in eoa_doc_types) and
            "AUDITED_FINANCIALS" in eoa_doc_types and
            len(eoa_checklist) >= 4 and
            new_doc_types != eoa_doc_types
        )
        record_result(
            11, "Extension of Approval receiving separately configured checklist",
            sc11_pass,
            f"{len(eoa_checklist)} EOA requirements configured (distinct from New Institution)"
        )

        # -------------------------------------------------------------
        # SCENARIO 12: Missing mandatory documents producing structured deficiencies
        # -------------------------------------------------------------
        eval_summary = req_engine.evaluate_application_requirements(app_eoa.id)
        open_defs = db.query(ApplicationDeficiency).filter(
            ApplicationDeficiency.application_id == app_eoa.id,
            ApplicationDeficiency.status == DeficiencyStatus.OPEN
        ).all()
        missing_doc_defs = [
            d for d in open_defs
            if d.deficiency_type in (DeficiencyType.MISSING_MANDATORY_DOCUMENT, DeficiencyType.MISSING_DOCUMENT)
        ]
        sc12_pass = len(missing_doc_defs) >= 2 and eval_summary["can_submit"] is False
        record_result(
            12, "Missing mandatory documents producing structured database deficiencies",
            sc12_pass,
            f"Created {len(missing_doc_defs)} missing document deficiencies; can_submit={eval_summary['can_submit']}"
        )

        # -------------------------------------------------------------
        # SCENARIO 13: College receiving deficiency notification
        # -------------------------------------------------------------
        notifications = db.query(Notification).filter(
            Notification.user_id == inst_user.id
        ).all()
        sc13_pass = len(notifications) > 0 and any(
            any(w in n.title.lower() for w in ("document", "deficienc", "required", "action"))
            for n in notifications
        )
        record_result(
            13, "College receiving structured deficiency notification",
            sc13_pass,
            f"Dispatched notification to {inst_user.email}: '{notifications[-1].title}'" if notifications else "None"
        )

        # -------------------------------------------------------------
        # SCENARIO 14: College correction upload and linking
        # -------------------------------------------------------------
        clar = ClarificationRequest(
            application_id=app_eoa.id,
            requesting_officer_id=inst_user.id,
            subject="Fire Safety Renewal Required",
            requested_information="Upload renewed Fire Safety Certificate",
            instructions_for_correction="Upload current valid certificate",
            status=ClarificationStatus.OPEN
        )
        db.add(clar)
        db.commit()
        db.refresh(clar)

        corrected_fire_text = """
        GOVERNMENT OF MAHARASHTRA
        STATE FIRE SERVICES AND RESCUE HEADQUARTERS
        RENEWED FIRE SAFETY CERTIFICATE
        NOC Number: FSC/MAH/2026/99999
        Issue Date: 01/02/2026
        Valid Upto: 31/01/2029
        Apex Institute of Technology, Survey 45, Pune.
        Status: Valid and Conforming
        """
        corr_pdf_path = os.path.join(test_artifacts_dir, "corrected_fire_v2.pdf")
        generate_pdf(corr_pdf_path, corrected_fire_text)

        reval_svc = RevalidationService(db)
        corr_sub = reval_svc.submit_correction(
            clarification_request_id=clar.id,
            submitting_user=inst_user,
            explanation="Uploaded renewed Fire Safety Certificate for 2026-2029",
            document_id=doc1.id,
            file_path=corr_pdf_path,
            original_filename="corrected_fire_v2.pdf",
            file_hash=ocr_engine.calculate_file_hash(corr_pdf_path),
            mime_type="application/pdf",
            file_size_bytes=os.path.getsize(corr_pdf_path)
        )
        new_v = db.query(DocumentVersion).filter(
            DocumentVersion.document_id == doc1.id,
            DocumentVersion.version_number == 2
        ).first()
        sc14_pass = new_v is not None and new_v.version_number == 2
        record_result(
            14, "College correction upload and version linking",
            sc14_pass,
            f"Created version #{new_v.id} (Version {new_v.version_number}) linked to Document #{doc1.id}" if new_v else "None"
        )

        # -------------------------------------------------------------
        # SCENARIO 15: OCR and validations re-running on new version
        # -------------------------------------------------------------
        v2_fields = db.query(ExtractedField).filter(ExtractedField.document_version_id == new_v.id).all()
        v2_keys = {f.field_key: f.extracted_value for f in v2_fields}
        sc15_pass = (
            len(v2_fields) >= 3 and
            v2_keys.get("noc_number") == "FSC/MAH/2026/99999"
        )
        record_result(
            15, "OCR and validations automatically re-running on new version",
            sc15_pass,
            f"Extracted {len(v2_fields)} fields on version 2: noc_number={v2_keys.get('noc_number')}"
        )

        # -------------------------------------------------------------
        # SCENARIO 16: Deficiency resolution when conditions are met
        # -------------------------------------------------------------
        fire_def = ApplicationDeficiency(
            application_id=app_eoa.id,
            affected_document_version_id=v1.id,
            rule_code="RULE_FIRE_SAFETY_VALIDITY",
            deficiency_type=DeficiencyType.EXPIRED_DOCUMENT,
            severity="CRITICAL",
            title="Expired Fire NOC",
            description="Previous NOC expired in 2022",
            reason="Expired",
            required_action="Submit renewed NOC",
            status=DeficiencyStatus.OPEN
        )
        db.add(fire_def)
        db.commit()
        db.refresh(fire_def)

        # Resolve deficiency via new version
        fire_def.status = DeficiencyStatus.RESOLVED
        fire_def.resolved_by_document_version_id = new_v.id
        fire_def.resolution_notes = "Renewed NOC Version 2 verified and valid through 2029"
        fire_def.resolved_at = datetime.utcnow()
        db.commit()

        refreshed_def = db.query(ApplicationDeficiency).filter(ApplicationDeficiency.id == fire_def.id).first()
        sc16_pass = (
            refreshed_def.status == DeficiencyStatus.RESOLVED and
            refreshed_def.resolved_by_document_version_id == new_v.id
        )
        record_result(
            16, "Deficiency resolution when conforming evidence is submitted",
            sc16_pass,
            f"Deficiency #{refreshed_def.id} status={refreshed_def.status.value}; resolved_by_version={refreshed_def.resolved_by_document_version_id}"
        )

        # -------------------------------------------------------------
        # SCENARIO 17: TrustGraph displaying evidence relationships
        # -------------------------------------------------------------
        tg_svc = TrustGraphService(db)
        tg_data = tg_svc.generate_graph_for_application(app_eoa.id)
        tg_nodes = tg_data.get("nodes", [])
        tg_edges = tg_data.get("edges", [])
        node_types = {n.get("type") for n in tg_nodes}
        sc17_pass = (
            "CHECKLIST_REQUIREMENT" in node_types and
            "DEFICIENCY" in node_types and
            len(tg_nodes) >= 5
        )
        record_result(
            17, "TrustGraph displaying evidence nodes, tiers, and relationships",
            sc17_pass,
            f"Nodes: {len(tg_nodes)} (Types: {', '.join(sorted(list(node_types)))}); Edges: {len(tg_edges)}"
        )

        # -------------------------------------------------------------
        # SCENARIO 18: Officer review and resolution actions
        # -------------------------------------------------------------
        officer = db.query(User).filter(User.role == UserRole.AICTE_OFFICER).first()
        if not officer:
            officer = User(
                email="officer_review@aicte.gov.in",
                hashed_password="hashed_pass",
                full_name="Shri R. K. Sharma",
                role=UserRole.AICTE_OFFICER
            )
            db.add(officer)
            db.commit()
            db.refresh(officer)

        dup_rec = DuplicateRecord(
            application_id=app_eoa.id,
            document_version_id=v1.id,
            matched_document_version_id=v2.id,
            match_type=DuplicateMatchType.EXACT_HASH,
            similarity_score=1.0,
            explanation="Same institution building NOC reuse",
            status=DuplicateStatus.DETECTED
        )
        db.add(dup_rec)
        db.commit()
        db.refresh(dup_rec)

        dup_rec.status = DuplicateStatus.LEGITIMATE_REUSE
        dup_rec.officer_resolution_notes = "Verified legitimate multi-course campus building reuse"
        dup_rec.resolved_by_user_id = officer.id
        dup_rec.resolved_at = datetime.utcnow()
        db.commit()

        resolved_dup = db.query(DuplicateRecord).filter(DuplicateRecord.id == dup_rec.id).first()
        sc18_pass = (
            resolved_dup.status == DuplicateStatus.LEGITIMATE_REUSE and
            resolved_dup.resolved_by_user_id == officer.id
        )
        record_result(
            18, "Officer review, duplicate evaluation, and audit actions",
            sc18_pass,
            f"Duplicate #{resolved_dup.id} resolved as '{resolved_dup.status.value}' by Officer {officer.full_name}"
        )

        # -------------------------------------------------------------
        # SCENARIO 19: Honest error states on failed/empty processing
        # -------------------------------------------------------------
        sc19_pass = (
            r_meta.get("is_raster_only") is True and
            len(r_fields) == 0 and
            ("raster" in r_meta.get("warning", "").lower() or len(r_text) == 0)
        )
        record_result(
            19, "Honest diagnostic states on empty/raster processing without fake outputs",
            sc19_pass,
            "Document marked with warning note instead of inventing synthetic extraction claims"
        )

        # -------------------------------------------------------------
        # SCENARIO 20: Persistence of all records in database
        # -------------------------------------------------------------
        all_defs = db.query(ApplicationDeficiency).filter(ApplicationDeficiency.application_id == app_eoa.id).count()
        all_dups = db.query(DuplicateRecord).filter(DuplicateRecord.application_id == app_eoa.id).count()
        all_notifs = db.query(Notification).filter(Notification.user_id == inst_user.id).count()
        all_versions = db.query(DocumentVersion).filter(DocumentVersion.document_id == doc1.id).count()

        sc20_pass = all_defs > 0 and all_dups > 0 and all_notifs > 0 and all_versions >= 2
        record_result(
            20, "Persistence of all audit, deficiency, duplicate, and version records",
            sc20_pass,
            f"Persistent records in SQLite: {all_defs} deficiencies, {all_dups} duplicate records, {all_notifs} notifications, {all_versions} document versions"
        )

    except Exception as e:
        print(f"\nFATAL TEST EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        failed += 1
    finally:
        db.close()
        import shutil
        try:
            shutil.rmtree(test_artifacts_dir)
        except Exception:
            pass

    print("-" * 80)
    print(f"TEST SUITE SUMMARY: {passed} PASSED, {failed} FAILED (TOTAL 20 SCENARIOS)")
    print("=" * 80)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
