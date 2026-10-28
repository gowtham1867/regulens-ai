import os
import uuid
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from sqlalchemy.orm import Session
from app.database import Base, engine, SessionLocal
from app.config import settings
from app.core.security import get_password_hash
from app.models.user import User, UserRole
from app.models.institution import Institution, InstitutionMembership
from app.models.application import (
    Application,
    ApplicationCategory,
    ApplicationStatus,
    ApplicationClaim
)
from app.models.document import (
    Document,
    DocumentVersion,
    ExtractedField,
    DocumentType,
    ProcessingStatus
)
from app.models.rule import (
    RegulatoryRule,
    RegulatoryRuleVersion,
    ApplicationChecklist,
    ChecklistRequirement,
    RuleCategory,
    RuleSeverity,
    EvaluationMethod
)
from app.models.finding import (
    ValidationRun,
    ValidationFinding,
    FindingEvidenceLink,
    FindingStatus,
    TriggerType
)
from app.models.verification import (
    VerificationSource,
    VerificationAttempt,
    VerificationOutcome,
    VerificationMethod
)
from app.models.workflow import (
    ClarificationRequest,
    ClarificationStatus,
    CorrectionSubmission,
    OfficerReview,
    WorkflowDecision
)
from app.models.audit import AuditEvent
from app.services.ocr_engine import OCREngine
from app.services.audit_service import record_audit_event


def create_synthetic_pdf(filepath: str, title: str, lines: list):
    """Generates an actual, readable PDF on disk using ReportLab."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    doc = SimpleDocTemplate(filepath, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    
    t_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0B2545'),
        alignment=1
    )
    b_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#172B4D')
    )

    story = [
        Paragraph(f"<b>GOVERNMENT / COMPETENT REGULATORY AUTHORITY</b>", styles['Normal']),
        Spacer(1, 10),
        Paragraph(title.upper(), t_style),
        Spacer(1, 15),
    ]

    for line in lines:
        story.append(Paragraph(line, b_style))
        story.append(Spacer(1, 8))

    doc.build(story)


def run_seed():
    db = SessionLocal()
    try:
        # Create all tables if not exist
        Base.metadata.create_all(bind=engine)

        print("[Seed] Checking existing data...")
        if db.query(User).filter(User.email == "admin@aicte-india.org").first():
            print("[Seed] Demo records already loaded.")
            return

        print("[Seed] Creating Regulatory Rules...")
        rules_data = [
            {
                "code": "AICTE-RULE-001-LAND-MANDATORY",
                "title": "Mandatory Land Document Title & Possession Check",
                "desc": "Verifies that institution has submitted legal title / registered continuous lease deed for campus land.",
                "category": RuleCategory.COMPLETENESS,
                "severity": RuleSeverity.CRITICAL,
                "method": EvaluationMethod.REQUIRED_DOCUMENT,
                "definition": "Require LAND_DOCUMENT with valid registration number"
            },
            {
                "code": "AICTE-RULE-002-FIRE-VALIDITY",
                "title": "Fire Safety Certificate Validity & Expiry Verification",
                "desc": "Ensures the Fire Safety Certificate issued by State Fire Services has not elapsed and remains valid throughout academic year.",
                "category": RuleCategory.VALIDITY,
                "severity": RuleSeverity.CRITICAL,
                "method": EvaluationMethod.VALIDITY_DATE_CHECK,
                "definition": "Require expiry_date >= current_date and authentic issuing authority"
            },
            {
                "code": "AICTE-RULE-003-NAME-CONSISTENCY",
                "title": "Cross-Document Institutional Name Consistency",
                "desc": "Detects discrepancies in institution title across land deeds, university letters, and official AICTE master registration.",
                "category": RuleCategory.CROSS_DOCUMENT,
                "severity": RuleSeverity.MAJOR,
                "method": EvaluationMethod.CROSS_DOCUMENT_MATCH,
                "definition": "Normalized token comparison between institution.name and extracted document fields >= 0.70"
            },
            {
                "code": "AICTE-RULE-004-LAND-THRESHOLD",
                "title": "Minimum Land Area Norm Compliance",
                "desc": "Evaluates whether total contiguous land meets minimum AICTE statutory requirement (7.5 Acres for technical campus).",
                "category": RuleCategory.COMPLIANCE,
                "severity": RuleSeverity.CRITICAL,
                "method": EvaluationMethod.THRESHOLD_EVALUATION,
                "definition": "land_area >= 7.5 Acres"
            },
            {
                "code": "AICTE-RULE-005-INTAKE-CONSISTENCY",
                "title": "Student Intake Sanction Consistency",
                "desc": "Validates that student intake requested in approval matches university affiliation sanction letter exactly.",
                "category": RuleCategory.CROSS_DOCUMENT,
                "severity": RuleSeverity.MAJOR,
                "method": EvaluationMethod.CROSS_DOCUMENT_MATCH,
                "definition": "application.declared_intake == extracted.approved_intake"
            }
        ]

        rules_map = {}
        for rd in rules_data:
            r = RegulatoryRule(
                rule_code=rd["code"],
                title=rd["title"],
                description=rd["desc"],
                category=rd["category"],
                severity=rd["severity"],
                evaluation_method=rd["method"],
                is_illustrative=True,
                official_source_ref="AICTE Approval Process Handbook (APH) 2025-2026",
                is_active=True
            )
            db.add(r)
            db.flush()
            rv = RegulatoryRuleVersion(
                rule_id=r.id,
                version_number=1,
                requirement_definition=rd["definition"],
                change_summary="Initial baseline regulatory rule version"
            )
            db.add(rv)
            rules_map[rd["code"]] = r

        print("[Seed] Creating Verification Sources...")
        v_sources = [
            VerificationSource(
                source_code="STATE_FIRE_SERVICES_PORTAL",
                name="Directorate of Fire and Rescue Services",
                authority_type="FIRE_SERVICE",
                verification_method=VerificationMethod.API_LOOKUP,
                is_simulated=True,
                simulated_badge_label="SIMULATED VERIFICATION — DEMONSTRATION DATA",
                is_available=True
            ),
            VerificationSource(
                source_code="STATE_REVENUE_LAND_REGISTRY",
                name="State Revenue & Land Records Registry",
                authority_type="REVENUE_LAND",
                verification_method=VerificationMethod.REPOSITORY_LOOKUP,
                is_simulated=True,
                simulated_badge_label="SIMULATED VERIFICATION — DEMONSTRATION DATA",
                is_available=True
            ),
            VerificationSource(
                source_code="AFFILIATING_UNIVERSITY_REGISTRY",
                name="Affiliating University Academic Council Registry",
                authority_type="UNIVERSITY",
                verification_method=VerificationMethod.API_LOOKUP,
                is_simulated=True,
                simulated_badge_label="SIMULATED VERIFICATION — DEMONSTRATION DATA",
                is_available=True
            )
        ]
        db.add_all(v_sources)
        db.flush()

        print("[Seed] Creating Demo Users...")
        admin_user = User(
            email="admin@aicte-india.org",
            hashed_password=get_password_hash("Admin@123"),
            full_name="Dr. Rajeshwar Sharma",
            role=UserRole.ADMINISTRATOR,
            designation="Director (Approval Bureau), AICTE",
            is_active=True
        )
        officer_user = User(
            email="officer@aicte-india.org",
            hashed_password=get_password_hash("Officer@123"),
            full_name="Priya V. Sundaram",
            role=UserRole.AICTE_OFFICER,
            designation="Senior Regulatory Scrutiny Officer",
            is_active=True
        )
        inst_user_apex = User(
            email="apex@institution.edu.in",
            hashed_password=get_password_hash("Institute@123"),
            full_name="Dr. K. Balasubramanian",
            role=UserRole.INSTITUTION_USER,
            designation="Principal & Authorized Representative",
            is_active=True
        )
        inst_user_zenith = User(
            email="zenith@institution.edu.in",
            hashed_password=get_password_hash("Institute@123"),
            full_name="Dr. Meera Natarajan",
            role=UserRole.INSTITUTION_USER,
            designation="Registrar, Zenith College",
            is_active=True
        )
        inst_user_vanguard = User(
            email="vanguard@institution.edu.in",
            hashed_password=get_password_hash("Institute@123"),
            full_name="Prof. Anand Deshmukh",
            role=UserRole.INSTITUTION_USER,
            designation="Dean of Academics",
            is_active=True
        )
        db.add_all([admin_user, officer_user, inst_user_apex, inst_user_zenith, inst_user_vanguard])
        db.flush()

        print("[Seed] Creating Institutions...")
        inst_apex = Institution(
            aicte_id="1-10972341",
            name="Apex Institute of Technology & Engineering",
            address="Plot 14-18, Rajiv Gandhi Salai, IT Corridor, Navalur",
            state="Tamil Nadu",
            district="Chengalpattu",
            pin_code="600130",
            institution_type="ENGINEERING_AND_TECHNOLOGY",
            established_year=2008,
            approval_status="APPROVED",
            contact_email="principal@apex.edu.in",
            contact_phone="+91-44-24508891",
            approved_intake=300,
            land_area_acres="10.5"
        )
        inst_zenith = Institution(
            aicte_id="1-24891032",
            name="Zenith College of Engineering & Research",
            address="SF No. 342, Avinashi Road, Peelamedu",
            state="Tamil Nadu",
            district="Coimbatore",
            pin_code="641004",
            institution_type="ENGINEERING_AND_TECHNOLOGY",
            established_year=2012,
            approval_status="APPROVED",
            contact_email="info@zenith.edu.in",
            contact_phone="+91-422-2589001",
            approved_intake=240,
            land_area_acres="6.2"
        )
        inst_vanguard = Institution(
            aicte_id="1-39108422",
            name="Vanguard Institute of Advanced Technology",
            address="Survey 88, Electronic City Phase 1",
            state="Karnataka",
            district="Bengaluru Urban",
            pin_code="560100",
            institution_type="ENGINEERING_AND_TECHNOLOGY",
            established_year=2015,
            approval_status="APPROVED",
            contact_email="admin@vanguard.ac.in",
            contact_phone="+91-80-28521040",
            approved_intake=360,
            land_area_acres="8.5"
        )
        db.add_all([inst_apex, inst_zenith, inst_vanguard])
        db.flush()

        # Memberships
        db.add(InstitutionMembership(user_id=inst_user_apex.id, institution_id=inst_apex.id, is_primary_contact=True))
        db.add(InstitutionMembership(user_id=inst_user_zenith.id, institution_id=inst_zenith.id, is_primary_contact=True))
        db.add(InstitutionMembership(user_id=inst_user_vanguard.id, institution_id=inst_vanguard.id, is_primary_contact=True))
        db.flush()

        # Storage directory
        storage_dir = settings.UPLOAD_DIR
        os.makedirs(storage_dir, exist_ok=True)

        # -------------------------------------------------------------
        # SCENARIO A: APPLICATION A (Complete & Passing)
        # -------------------------------------------------------------
        print("[Seed] Creating Application A (Complete Application)...")
        app_a = Application(
            reference_no="AICTE-2025-APP-001",
            institution_id=inst_apex.id,
            submitting_user_id=inst_user_apex.id,
            assigned_officer_id=officer_user.id,
            title="Extension of Approval (EoA) 2025-2026 for Apex Institute",
            category=ApplicationCategory.EXTENSION_OF_APPROVAL,
            academic_year="2025-2026",
            status=ApplicationStatus.UNDER_REVIEW,
            declared_intake=300,
            declared_land_acres=10.5,
            declared_built_up_sqm=12500.0,
            declared_faculty_count=82,
            is_demo_seed=True,
            submission_date=datetime.utcnow() - timedelta(days=5),
            notes="Annual Extension of Approval submitted with updated unencumbered land deeds and current fire NOC."
        )
        db.add(app_a)
        db.flush()

        # Generate Real PDFs for Application A
        pdf_a_fire = os.path.join(storage_dir, "apex_fire_noc_2025.pdf")
        create_synthetic_pdf(
            pdf_a_fire,
            "Fire Safety Certificate / No Objection Certificate",
            [
                "Certificate No: FS-TN-2024-8841",
                "Issuing Authority: Directorate of Fire & Rescue Services, Tamil Nadu",
                "Issued to: Apex Institute of Technology & Engineering",
                "AICTE ID: 1-10972341",
                "Date of Issue: 15-05-2024",
                "Valid Upto: 30-06-2026",
                "Certified that the premises comprising 4 instructional blocks have been inspected and comply with National Building Code safety norms."
            ]
        )
        with open(pdf_a_fire, "rb") as f:
            bytes_fire_a = f.read()
        hash_fire_a = OCREngine.calculate_file_hash(bytes_fire_a)

        doc_a_fire = Document(application_id=app_a.id, document_type=DocumentType.FIRE_SAFETY_CERTIFICATE, title="Fire Safety NOC Certificate", is_required=True)
        db.add(doc_a_fire)
        db.flush()
        ver_a_fire = DocumentVersion(
            document_id=doc_a_fire.id,
            version_number=1,
            file_path=pdf_a_fire,
            original_filename="Apex_Fire_Safety_NOC_2024.pdf",
            file_hash=hash_fire_a,
            mime_type="application/pdf",
            file_size_bytes=len(bytes_fire_a),
            status=ProcessingStatus.COMPLETED,
            ocr_confidence=0.96,
            page_count=1
        )
        db.add(ver_a_fire)
        db.flush()

        db.add(ExtractedField(document_version_id=ver_a_fire.id, field_key="certificate_number", field_label="Certificate Number", extracted_value="FS-TN-2024-8841", normalized_value="FS-TN-2024-8841", source_page=1, confidence=0.98))
        db.add(ExtractedField(document_version_id=ver_a_fire.id, field_key="institution_name", field_label="Institution Name", extracted_value="Apex Institute of Technology & Engineering", normalized_value="Apex Institute of Technology & Engineering", source_page=1, confidence=0.95))
        db.add(ExtractedField(document_version_id=ver_a_fire.id, field_key="issue_date", field_label="Date of Issue", extracted_value="15-05-2024", normalized_value="2024-05-15", source_page=1, confidence=0.94))
        db.add(ExtractedField(document_version_id=ver_a_fire.id, field_key="expiry_date", field_label="Expiry Date", extracted_value="30-06-2026", normalized_value="2026-06-30", source_page=1, confidence=0.96))

        # Land Document for App A
        pdf_a_land = os.path.join(storage_dir, "apex_land_deed.pdf")
        create_synthetic_pdf(
            pdf_a_land,
            "Registered Land Ownership & Title Deed",
            [
                "Document No: REV-LAND-90214",
                "Sub-Registrar Office: Sriperumbudur SRO",
                "Institution Name: Apex Institute of Technology & Engineering",
                "Total Land Area: 10.5 Acres",
                "Survey No: 42/1B, 42/2",
                "Date of Issue: 12-08-2007",
                "Schedule: Contiguous freehold title with boundary wall demarcating technical campus."
            ]
        )
        with open(pdf_a_land, "rb") as f:
            bytes_land_a = f.read()
        hash_land_a = OCREngine.calculate_file_hash(bytes_land_a)

        doc_a_land = Document(application_id=app_a.id, document_type=DocumentType.LAND_DOCUMENT, title="Registered Campus Land Title Deed", is_required=True)
        db.add(doc_a_land)
        db.flush()
        ver_a_land = DocumentVersion(
            document_id=doc_a_land.id,
            version_number=1,
            file_path=pdf_a_land,
            original_filename="Apex_Registered_Land_Deed.pdf",
            file_hash=hash_land_a,
            mime_type="application/pdf",
            file_size_bytes=len(bytes_land_a),
            status=ProcessingStatus.COMPLETED,
            ocr_confidence=0.95,
            page_count=1
        )
        db.add(ver_a_land)
        db.flush()

        db.add(ExtractedField(document_version_id=ver_a_land.id, field_key="certificate_number", field_label="Document No", extracted_value="REV-LAND-90214", normalized_value="REV-LAND-90214", source_page=1, confidence=0.95))
        db.add(ExtractedField(document_version_id=ver_a_land.id, field_key="institution_name", field_label="Institution Name", extracted_value="Apex Institute of Technology & Engineering", normalized_value="Apex Institute of Technology & Engineering", source_page=1, confidence=0.96))
        db.add(ExtractedField(document_version_id=ver_a_land.id, field_key="land_area", field_label="Total Land Area", extracted_value="10.5 Acres", normalized_value="10.5", source_page=1, confidence=0.97))

        # Affiliation Certificate for App A
        pdf_a_affil = os.path.join(storage_dir, "apex_affiliation_letter.pdf")
        create_synthetic_pdf(
            pdf_a_affil,
            "University Provisional Affiliation Order",
            [
                "Reference Number: AFF-UNIV-2024-118",
                "Issuing Authority: Anna University, Chennai",
                "Institution Name: Apex Institute of Technology & Engineering",
                "Academic Year: 2025-2026",
                "Approved Intake: 300 Seats",
                "Date of Issue: 20-04-2024",
                "Sanction granted for B.E. Computer Science, B.Tech AI & Data Science, B.E. Mechanical Engineering."
            ]
        )
        with open(pdf_a_affil, "rb") as f:
            bytes_affil_a = f.read()
        hash_affil_a = OCREngine.calculate_file_hash(bytes_affil_a)

        doc_a_affil = Document(application_id=app_a.id, document_type=DocumentType.AFFILIATION_CERTIFICATE, title="University Affiliation Sanction Order", is_required=True)
        db.add(doc_a_affil)
        db.flush()
        ver_a_affil = DocumentVersion(
            document_id=doc_a_affil.id,
            version_number=1,
            file_path=pdf_a_affil,
            original_filename="Apex_Anna_University_Affiliation_2025.pdf",
            file_hash=hash_affil_a,
            mime_type="application/pdf",
            file_size_bytes=len(bytes_affil_a),
            status=ProcessingStatus.COMPLETED,
            ocr_confidence=0.96,
            page_count=1
        )
        db.add(ver_a_affil)
        db.flush()

        db.add(ExtractedField(document_version_id=ver_a_affil.id, field_key="certificate_number", field_label="Reference Number", extracted_value="AFF-UNIV-2024-118", normalized_value="AFF-UNIV-2024-118", source_page=1, confidence=0.97))
        db.add(ExtractedField(document_version_id=ver_a_affil.id, field_key="institution_name", field_label="Institution Name", extracted_value="Apex Institute of Technology & Engineering", normalized_value="Apex Institute of Technology & Engineering", source_page=1, confidence=0.95))
        db.add(ExtractedField(document_version_id=ver_a_affil.id, field_key="approved_intake", field_label="Approved Student Intake", extracted_value="300 Seats", normalized_value="300", source_page=1, confidence=0.96))

        # Verification attempt for App A
        att_a = VerificationAttempt(
            document_version_id=ver_a_fire.id,
            verification_source_id=v_sources[0].id,
            certificate_number="FS-TN-2024-8841",
            verification_method=VerificationMethod.API_LOOKUP,
            outcome=VerificationOutcome.VERIFIED,
            cache_key="apex_fire_verified_hash_key",
            is_reused=False,
            is_simulated=True,
            evidence_payload='{"certificate_number": "FS-TN-2024-8841", "issuing_office": "Anna Nagar Station", "issued_to": "Apex Institute", "status": "AUTHENTIC_ACTIVE"}',
            request_timestamp=datetime.utcnow() - timedelta(days=2),
            response_timestamp=datetime.utcnow() - timedelta(days=2)
        )
        db.add(att_a)

        # Validation Run for App A
        run_a = ValidationRun(
            application_id=app_a.id,
            run_number=1,
            trigger_type=TriggerType.INITIAL_VALIDATION,
            triggering_change="Initial submission scrutiny",
            total_rules_evaluated=5,
            passed_count=5,
            failed_count=0,
            warning_count=0,
            manual_review_count=0,
            executed_at=datetime.utcnow() - timedelta(days=2)
        )
        db.add(run_a)
        db.flush()

        # All 5 findings pass for App A
        for r_code, r_obj in rules_map.items():
            f_a = ValidationFinding(
                validation_run_id=run_a.id,
                application_id=app_a.id,
                rule_id=r_obj.id,
                status=FindingStatus.PASSED,
                severity=r_obj.severity.value,
                explanation=f"All requirements under {r_obj.title} satisfied by submitted evidence.",
                is_active=True,
                is_resolved=True
            )
            db.add(f_a)

        # -------------------------------------------------------------
        # SCENARIO B: APPLICATION B (Deficiencies & Mismatch)
        # -------------------------------------------------------------
        print("[Seed] Creating Application B (Deficiencies & Discrepancies)...")
        app_b = Application(
            reference_no="AICTE-2025-APP-002",
            institution_id=inst_zenith.id,
            submitting_user_id=inst_user_zenith.id,
            assigned_officer_id=officer_user.id,
            title="Extension of Approval (EoA) 2025-2026 for Zenith College",
            category=ApplicationCategory.EXTENSION_OF_APPROVAL,
            academic_year="2025-2026",
            status=ApplicationStatus.CLARIFICATION_REQUESTED,
            declared_intake=360,  # Conflict: baseline is 240!
            declared_land_acres=6.2,  # Conflict: Below 7.5 Acres!
            declared_built_up_sqm=7100.0,
            declared_faculty_count=55,
            is_demo_seed=True,
            submission_date=datetime.utcnow() - timedelta(days=4),
            notes="Institutional submission with expired safety certificate and land acreage shortfall."
        )
        db.add(app_b)
        db.flush()

        # Real PDF with Expired Fire Certificate for App B
        pdf_b_fire = os.path.join(storage_dir, "zenith_fire_expired.pdf")
        create_synthetic_pdf(
            pdf_b_fire,
            "State Fire & Rescue Services — Clearance Record",
            [
                "Certificate No: FS-TN-2022-1029",
                "Issuing Authority: Department of Fire Services, Western Region",
                "Premises: Sunrise Polymers Warehouse & Compound",
                "Date of Issue: 10-01-2022",
                "Valid Upto: 15-01-2023",
                "NOTE: Clearance expired on 15-Jan-2023. Not renewed for academic educational occupancy."
            ]
        )
        with open(pdf_b_fire, "rb") as f:
            bytes_fire_b = f.read()
        hash_fire_b = OCREngine.calculate_file_hash(bytes_fire_b)

        doc_b_fire = Document(application_id=app_b.id, document_type=DocumentType.FIRE_SAFETY_CERTIFICATE, title="Fire Safety Clearance Certificate", is_required=True)
        db.add(doc_b_fire)
        db.flush()
        ver_b_fire = DocumentVersion(
            document_id=doc_b_fire.id,
            version_number=1,
            file_path=pdf_b_fire,
            original_filename="Zenith_Fire_NOC_2022.pdf",
            file_hash=hash_fire_b,
            mime_type="application/pdf",
            file_size_bytes=len(bytes_fire_b),
            status=ProcessingStatus.COMPLETED,
            ocr_confidence=0.94,
            page_count=1
        )
        db.add(ver_b_fire)
        db.flush()

        db.add(ExtractedField(document_version_id=ver_b_fire.id, field_key="certificate_number", field_label="Certificate No", extracted_value="FS-TN-2022-1029", normalized_value="FS-TN-2022-1029", source_page=1, confidence=0.98))
        db.add(ExtractedField(document_version_id=ver_b_fire.id, field_key="institution_name", field_label="Premises Name", extracted_value="Sunrise Polymers Warehouse", normalized_value="Sunrise Polymers Warehouse", source_page=1, confidence=0.90))
        db.add(ExtractedField(document_version_id=ver_b_fire.id, field_key="expiry_date", field_label="Expiry Date", extracted_value="15-01-2023", normalized_value="2023-01-15", source_page=1, confidence=0.96))

        # Real PDF with Land Document for App B (6.2 Acres)
        pdf_b_land = os.path.join(storage_dir, "zenith_land_shortfall.pdf")
        create_synthetic_pdf(
            pdf_b_land,
            "Revenue Department — Title Deed Schedule",
            [
                "Document No: REV-LAND-61099",
                "Institution Name: Zenith College of Engineering & Research",
                "Total Land Area: 6.2 Acres",
                "Survey No: 342/1",
                "Date of Issue: 18-09-2011",
                "Schedule: Compact campus parcel measuring 6.20 continuous acres."
            ]
        )
        with open(pdf_b_land, "rb") as f:
            bytes_land_b = f.read()
        hash_land_b = OCREngine.calculate_file_hash(bytes_land_b)

        doc_b_land = Document(application_id=app_b.id, document_type=DocumentType.LAND_DOCUMENT, title="Campus Title Deed", is_required=True)
        db.add(doc_b_land)
        db.flush()
        ver_b_land = DocumentVersion(
            document_id=doc_b_land.id,
            version_number=1,
            file_path=pdf_b_land,
            original_filename="Zenith_Land_Record.pdf",
            file_hash=hash_land_b,
            mime_type="application/pdf",
            file_size_bytes=len(bytes_land_b),
            status=ProcessingStatus.COMPLETED,
            ocr_confidence=0.93,
            page_count=1
        )
        db.add(ver_b_land)
        db.flush()

        db.add(ExtractedField(document_version_id=ver_b_land.id, field_key="land_area", field_label="Total Land Area", extracted_value="6.2 Acres", normalized_value="6.2", source_page=1, confidence=0.95))

        # Verification attempt for App B (Mismatch detected by adapter)
        att_b = VerificationAttempt(
            document_version_id=ver_b_fire.id,
            verification_source_id=v_sources[0].id,
            certificate_number="FS-TN-2022-1029",
            verification_method=VerificationMethod.API_LOOKUP,
            outcome=VerificationOutcome.MISMATCH_DETECTED,
            is_reused=False,
            is_simulated=True,
            failure_reason="Registry record belongs to 'Sunrise Polymers Warehouse' and expired on 15-Jan-2023.",
            evidence_payload='{"certificate_number": "FS-TN-2022-1029", "registered_owner": "Sunrise Polymers Warehouse", "status": "EXPIRED"}',
            request_timestamp=datetime.utcnow() - timedelta(days=3),
            response_timestamp=datetime.utcnow() - timedelta(days=3)
        )
        db.add(att_b)

        # Validation Run for App B
        run_b = ValidationRun(
            application_id=app_b.id,
            run_number=1,
            trigger_type=TriggerType.INITIAL_VALIDATION,
            triggering_change="Initial scrutiny",
            total_rules_evaluated=5,
            passed_count=2,
            failed_count=2,
            warning_count=1,
            manual_review_count=0,
            executed_at=datetime.utcnow() - timedelta(days=3)
        )
        db.add(run_b)
        db.flush()

        f_b1 = ValidationFinding(
            validation_run_id=run_b.id,
            application_id=app_b.id,
            rule_id=rules_map["AICTE-RULE-002-FIRE-VALIDITY"].id,
            status=FindingStatus.FAILED,
            severity="CRITICAL",
            affected_claim_field="expiry_date",
            affected_document_version_id=ver_b_fire.id,
            expected_value="Valid through academic year 2025-2026",
            observed_value="Expired on 2023-01-15",
            explanation="Fire Safety Certificate expired on 15-Jan-2023. Issuing authority registry indicates premises registered to a different warehouse commercial entity.",
            recommended_action="Submit renewed Fire Safety NOC issued specifically to Zenith College of Engineering.",
            is_active=True,
            is_resolved=False
        )
        f_b2 = ValidationFinding(
            validation_run_id=run_b.id,
            application_id=app_b.id,
            rule_id=rules_map["AICTE-RULE-004-LAND-THRESHOLD"].id,
            status=FindingStatus.FAILED,
            severity="CRITICAL",
            affected_claim_field="land_area",
            affected_document_version_id=ver_b_land.id,
            expected_value=">= 7.5 Acres",
            observed_value="6.2 Acres",
            explanation="Extracted land area (6.2 Acres) fails minimum statutory norm of 7.5 Acres for technical engineering institutions.",
            recommended_action="Provide registered contiguous land deed or government urban relaxation order.",
            is_active=True,
            is_resolved=False
        )
        f_b3 = ValidationFinding(
            validation_run_id=run_b.id,
            application_id=app_b.id,
            rule_id=rules_map["AICTE-RULE-003-NAME-CONSISTENCY"].id,
            status=FindingStatus.WARNING,
            severity="MAJOR",
            affected_claim_field="institution_name",
            affected_document_version_id=ver_b_fire.id,
            expected_value="Zenith College of Engineering & Research",
            observed_value="Sunrise Polymers Warehouse",
            explanation="Premises title in fire certificate ('Sunrise Polymers Warehouse') conflicts with institutional master name.",
            recommended_action="Seek clarification on ownership link or lease agreement.",
            is_active=True,
            is_resolved=False
        )
        db.add_all([f_b1, f_b2, f_b3])
        db.flush()

        # Clarification Request created for App B by Officer
        clar_b = ClarificationRequest(
            application_id=app_b.id,
            requesting_officer_id=officer_user.id,
            subject="Urgent: Lapsed Fire Safety NOC & Land Area Shortfall Deficiencies",
            requested_information="1. Valid Fire NOC issued by Directorate of Fire Services for 2025-2026. 2. Justification and survey records for 6.2 Acres shortfall.",
            instructions_for_correction="Upload high-resolution renewed Fire Safety Certificate clearly naming Zenith College of Engineering. Ensure certificate validity extends through academic period.",
            relevant_finding_id=f_b1.id,
            relevant_document_id=doc_b_fire.id,
            status=ClarificationStatus.OPEN,
            due_date=datetime.utcnow() + timedelta(days=7),
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(clar_b)

        # -------------------------------------------------------------
        # SCENARIO C: APPLICATION C (Correction & Revalidation Ready)
        # -------------------------------------------------------------
        print("[Seed] Creating Application C (Correction & Revalidation Complete)...")
        app_c = Application(
            reference_no="AICTE-2025-APP-003",
            institution_id=inst_vanguard.id,
            submitting_user_id=inst_user_vanguard.id,
            assigned_officer_id=officer_user.id,
            title="Extension of Approval (EoA) 2025-2026 for Vanguard Institute",
            category=ApplicationCategory.EXTENSION_OF_APPROVAL,
            academic_year="2025-2026",
            status=ApplicationStatus.READY_FOR_DECISION,
            declared_intake=360,
            declared_land_acres=8.5,
            declared_built_up_sqm=10400.0,
            declared_faculty_count=78,
            is_demo_seed=True,
            submission_date=datetime.utcnow() - timedelta(days=10),
            notes="Correction submitted: Version 2 of Fire Safety Certificate uploaded in response to Clarification #1."
        )
        db.add(app_c)
        db.flush()

        # Doc C Fire Version 1 (Lapsed)
        pdf_c_fire_v1 = os.path.join(storage_dir, "vanguard_fire_v1_lapsed.pdf")
        create_synthetic_pdf(
            pdf_c_fire_v1,
            "Karnataka State Fire & Emergency Services",
            [
                "Certificate No: FS-KA-2023-4011",
                "Institution Name: Vanguard Institute of Advanced Technology",
                "Date of Issue: 01-03-2023",
                "Valid Upto: 28-02-2024",
                "Certificate validity expired on 28-Feb-2024."
            ]
        )
        with open(pdf_c_fire_v1, "rb") as f:
            b_c1 = f.read()
        h_c1 = OCREngine.calculate_file_hash(b_c1)

        doc_c_fire = Document(application_id=app_c.id, document_type=DocumentType.FIRE_SAFETY_CERTIFICATE, title="Fire Safety Clearance", is_required=True)
        db.add(doc_c_fire)
        db.flush()
        ver_c_fire_v1 = DocumentVersion(
            document_id=doc_c_fire.id,
            version_number=1,
            file_path=pdf_c_fire_v1,
            original_filename="Vanguard_Fire_NOC_2023_v1.pdf",
            file_hash=h_c1,
            mime_type="application/pdf",
            file_size_bytes=len(b_c1),
            status=ProcessingStatus.COMPLETED,
            ocr_confidence=0.95,
            page_count=1
        )
        db.add(ver_c_fire_v1)
        db.flush()

        # Clarification Request for App C
        clar_c = ClarificationRequest(
            application_id=app_c.id,
            requesting_officer_id=officer_user.id,
            subject="Expired Fire NOC on Record",
            requested_information="Updated 2025-2026 Fire Safety Clearance",
            instructions_for_correction="Upload current renewal certificate.",
            status=ClarificationStatus.RESPONDED,
            created_at=datetime.utcnow() - timedelta(days=6)
        )
        db.add(clar_c)
        db.flush()

        # Correction Submission for App C
        corr_c = CorrectionSubmission(
            clarification_request_id=clar_c.id,
            application_id=app_c.id,
            submitting_user_id=inst_user_vanguard.id,
            explanation="Uploaded latest renewal NOC FS-KA-2025-9912 issued on 10-Jan-2025 by Fire Commissioner, valid through 2026.",
            created_at=datetime.utcnow() - timedelta(days=3)
        )
        db.add(corr_c)
        db.flush()

        # Real PDF for Version 2 (Valid Renewal!)
        pdf_c_fire_v2 = os.path.join(storage_dir, "vanguard_fire_v2_renewed.pdf")
        create_synthetic_pdf(
            pdf_c_fire_v2,
            "Karnataka State Fire & Emergency Services — Annual Renewal",
            [
                "Certificate No: FS-KA-2025-9912",
                "Issuing Authority: Office of the Director General of Police, Fire & Emergency Services",
                "Institution Name: Vanguard Institute of Advanced Technology",
                "Date of Issue: 10-01-2025",
                "Valid Upto: 31-12-2026",
                "RENEWAL CONFIRMED: Building conforms to all fire exit, smoke detector, and sprinkler norms."
            ]
        )
        with open(pdf_c_fire_v2, "rb") as f:
            b_c2 = f.read()
        h_c2 = OCREngine.calculate_file_hash(b_c2)

        ver_c_fire_v2 = DocumentVersion(
            document_id=doc_c_fire.id,
            version_number=2,
            file_path=pdf_c_fire_v2,
            original_filename="Vanguard_Fire_NOC_Renewed_2025_v2.pdf",
            file_hash=h_c2,
            mime_type="application/pdf",
            file_size_bytes=len(b_c2),
            status=ProcessingStatus.COMPLETED,
            ocr_confidence=0.98,
            page_count=1,
            correction_submission_id=corr_c.id
        )
        db.add(ver_c_fire_v2)
        db.flush()

        db.add(ExtractedField(document_version_id=ver_c_fire_v2.id, field_key="certificate_number", field_label="Certificate No", extracted_value="FS-KA-2025-9912", normalized_value="FS-KA-2025-9912", source_page=1, confidence=0.98))
        db.add(ExtractedField(document_version_id=ver_c_fire_v2.id, field_key="expiry_date", field_label="Expiry Date", extracted_value="31-12-2026", normalized_value="2026-12-31", source_page=1, confidence=0.97))
        db.add(ExtractedField(document_version_id=ver_c_fire_v2.id, field_key="institution_name", field_label="Institution Name", extracted_value="Vanguard Institute of Advanced Technology", normalized_value="Vanguard Institute of Advanced Technology", source_page=1, confidence=0.96))

        # Revalidation Run for App C
        run_c2 = ValidationRun(
            application_id=app_c.id,
            run_number=2,
            trigger_type=TriggerType.CHANGE_AWARE_REVALIDATION,
            triggering_change="Selective revalidation on corrected Fire NOC v2",
            total_rules_evaluated=5,
            passed_count=5,
            failed_count=0,
            reused_checks_count=4,
            reexecuted_checks_count=1,
            executed_at=datetime.utcnow() - timedelta(days=2)
        )
        db.add(run_c2)
        db.flush()

        # Historic finding (v1 expired) preserved as superseded & resolved
        f_c_historic = ValidationFinding(
            validation_run_id=run_c2.id,
            application_id=app_c.id,
            rule_id=rules_map["AICTE-RULE-002-FIRE-VALIDITY"].id,
            status=FindingStatus.SUPERSEDED,
            severity="CRITICAL",
            affected_claim_field="expiry_date",
            affected_document_version_id=ver_c_fire_v1.id,
            expected_value="Valid beyond 2025",
            observed_value="Expired on 2024-02-28 (v1)",
            explanation="Superseded: Earlier Document Version 1 expired on 28-Feb-2024. Replaced by Version 2.",
            is_active=False,
            is_resolved=True
        )
        # Active new finding (v2 valid)
        f_c_active = ValidationFinding(
            validation_run_id=run_c2.id,
            application_id=app_c.id,
            rule_id=rules_map["AICTE-RULE-002-FIRE-VALIDITY"].id,
            status=FindingStatus.PASSED,
            severity="INFO",
            affected_claim_field="expiry_date",
            affected_document_version_id=ver_c_fire_v2.id,
            expected_value="Valid beyond 2025",
            observed_value="Valid until 2026-12-31 (v2)",
            explanation="Resolved: Corrected Fire NOC Version 2 is current and valid until 31-Dec-2026.",
            is_active=True,
            is_resolved=True
        )
        db.add_all([f_c_historic, f_c_active])

        # Verification reuse demo for App C
        att_c = VerificationAttempt(
            document_version_id=ver_c_fire_v2.id,
            verification_source_id=v_sources[0].id,
            certificate_number="FS-KA-2025-9912",
            verification_method=VerificationMethod.API_LOOKUP,
            outcome=VerificationOutcome.VERIFIED,
            cache_key="vanguard_v2_cache_key",
            is_reused=False,
            is_simulated=True,
            evidence_payload='{"certificate_number": "FS-KA-2025-9912", "status": "VERIFIED_ACTIVE"}',
            request_timestamp=datetime.utcnow() - timedelta(days=2),
            response_timestamp=datetime.utcnow() - timedelta(days=2)
        )
        db.add(att_c)

        db.commit()
        print("[Seed] Seed data generation completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"[Seed] Error creating seed data: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()

