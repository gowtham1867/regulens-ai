import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.application import Application, ApplicationCategory
from app.models.document import Document, DocumentVersion, ExtractedField, DocumentType, ProcessingStatus
from app.models.rule import ApplicationChecklist, ChecklistRequirement, RegulatoryRule
from app.models.deficiency import ApplicationDeficiency, DeficiencyType, DeficiencyStatus
from app.models.institution import InstitutionMembership
from app.services.notification_service import create_notification

logger = logging.getLogger(__name__)


# Official AICTE Approval Process Handbook (APH 2024–27) Baseline Checklists
CHECKLIST_DEFINITIONS = {
    "NEW_INSTITUTION": {
        "title": "Establishment of New Technical Institution — APH 2024–27 Checklist",
        "academic_year": "2025-2026",
        "requirements": [
            {
                "document_type": "LAND_DOCUMENT",
                "requirement_title": "Registered Land Ownership Title Deed or Continuous Lease Deed (>= 30 Years)",
                "requirement_description": "Clear and undisputed land ownership deed in the name of the Applicant Society/Trust registered at the Sub-Registrar Office. Minimum 7.5 acres in rural or 4.0 acres in urban locations as per APH Table 2.1.",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["certificate_number", "institution_name", "land_area", "issuing_authority"],
                "validation_criteria": "Land area must meet APH threshold (rural >= 7.5 acres, urban >= 4 acres). Title must be registered.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter II, Section 2.3.1 (Land Norms)",
                "order_index": 1
            },
            {
                "document_type": "LAND_USE_CERTIFICATE",
                "requirement_title": "Land Use / Conversion Certificate (CLU) from Competent Revenue Authority",
                "requirement_description": "Certificate from District Collector / Sub-Divisional Magistrate / Tahsildar confirming permitted institutional / educational land use under applicable State Land Revenue Code.",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["certificate_number", "issuing_authority", "land_use_classification"],
                "validation_criteria": "Land use must explicitly state 'Educational' or 'Institutional'.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter II, Section 2.3.4 (Zoning & CLU)",
                "order_index": 2
            },
            {
                "document_type": "BUILDING_PLAN",
                "requirement_title": "Master Approved Building Plan Sanctioned by Town Planning / Municipal Authority",
                "requirement_description": "Approved architectural and structural drawing by the competent local urban planning authority or District Town & Country Planning (DTCP).",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["certificate_number", "issuing_authority", "built_up_area_sqm"],
                "validation_criteria": "Sanctioned built-up area must support instructional, administrative, and amenities space norms.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter II, Section 2.4 (Building & Space Norms)",
                "order_index": 3
            },
            {
                "document_type": "OCCUPANCY_CERTIFICATE",
                "requirement_title": "Building Occupancy / Completion Certificate from Competent Authority",
                "requirement_description": "Occupancy or fitness for use certificate issued by the local Municipal Corporation / Municipality / District Administration.",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["certificate_number", "issuing_authority", "issue_date"],
                "validation_criteria": "Must confirm building is fully completed and fit for educational occupation.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter II, Section 2.4.6",
                "order_index": 4
            },
            {
                "document_type": "FIRE_SAFETY_CERTIFICATE",
                "requirement_title": "Fire Safety Clearance NOC from State Directorate of Fire Services",
                "requirement_description": "Valid Fire Safety No Objection Certificate (NOC) issued by the State Fire Services Department or Municipal Fire Officer complying with National Building Code (NBC 2016 Part 4).",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["certificate_number", "issuing_authority", "issue_date", "expiry_date"],
                "validation_criteria": "Certificate validity must not be expired on the date of application scrutiny.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter II, Section 2.5 (Safety Standards)",
                "order_index": 5
            },
            {
                "document_type": "AUDITED_FINANCIALS",
                "requirement_title": "Audited Financial Statements & Corpus Fund Guarantee by Chartered Accountant",
                "requirement_description": "Balance Sheet, Income & Expenditure Statement, and Fixed Deposit Receipt (FDR) / Corpus Fund in joint name with AICTE certified with ICAI UDIN.",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["ca_firm_name", "ca_udin"],
                "validation_criteria": "Valid CA certification with 18-character ICAI UDIN number.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter II, Section 2.7 (Financial Norms)",
                "order_index": 6
            }
        ]
    },
    "EXTENSION_OF_APPROVAL": {
        "title": "Extension of Approval (EoA) — APH 2024–27 Annual Compliance Checklist",
        "academic_year": "2025-2026",
        "requirements": [
            {
                "document_type": "FIRE_SAFETY_CERTIFICATE",
                "requirement_title": "Renewed Fire Safety Certificate / NOC for Current Academic Cycle",
                "requirement_description": "Active, renewed Fire Safety NOC from State Fire Services ensuring fire-fighting installations and emergency evacuation compliance.",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["certificate_number", "issuing_authority", "expiry_date"],
                "validation_criteria": "Validity date must be active and unexpired throughout academic scrutiny window.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter IV, Section 4.2.1 (Annual Clearances)",
                "order_index": 1
            },
            {
                "document_type": "AFFILIATION_CERTIFICATE",
                "requirement_title": "University Affiliation Order / Sanction Notification for Applicable Year",
                "requirement_description": "Affiliation order issued by the affiliating State University or Technological University specifying approved programs and sanctioned intake.",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["certificate_number", "affiliating_university", "approved_intake"],
                "validation_criteria": "Affiliated intake must not be less than declared institutional enrollment claims.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter IV, Section 4.3 (University Affiliation)",
                "order_index": 2
            },
            {
                "document_type": "AUDITED_FINANCIALS",
                "requirement_title": "Audited Financial Statements of Preceding Financial Year with UDIN",
                "requirement_description": "Audited balance sheet and income statement evidencing operational sustainability, faculty salary disbursement, and lab upkeep.",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["ca_firm_name", "ca_udin"],
                "validation_criteria": "Must contain verifiable CA certification and UDIN.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter IV, Section 4.5",
                "order_index": 3
            },
            {
                "document_type": "LAND_DOCUMENT",
                "requirement_title": "Verified Master Land Title Record or Valid Continuous Lease Confirmation",
                "requirement_description": "Re-verification of institutional land continuity to confirm absence of unauthorized alienation or encumbrances.",
                "is_mandatory": False,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["certificate_number", "land_area"],
                "validation_criteria": "Land extent must equal or exceed established baseline (10.5 acres for Apex Institute).",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter IV, Section 4.1",
                "order_index": 4
            }
        ]
    },
    "INCREASE_IN_INTAKE": {
        "title": "Increase in Intake / Additional Division — APH 2024–27 Checklist",
        "academic_year": "2025-2026",
        "requirements": [
            {
                "document_type": "AFFILIATION_CERTIFICATE",
                "requirement_title": "University Sanction for Enhanced Student Intake",
                "requirement_description": "Formal resolution and inspection report from affiliating University recommending increase in enrollment capacity.",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["certificate_number", "affiliating_university", "approved_intake"],
                "validation_criteria": "University approved intake must match or exceed declared intake expansion.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter V, Section 5.1",
                "order_index": 1
            },
            {
                "document_type": "BUILDING_PLAN",
                "requirement_title": "Additional Built-up & Instructional Area Verification",
                "requirement_description": "Architect certified floor plan proving additional classrooms and labs commensurate with expanded student strength.",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["built_up_area_sqm", "issuing_authority"],
                "validation_criteria": "Built-up area must meet student-to-space ratio as per APH Annexure 4.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter V, Section 5.3",
                "order_index": 2
            },
            {
                "document_type": "FIRE_SAFETY_CERTIFICATE",
                "requirement_title": "Fire Safety NOC Covering Expanded Institutional Facilities",
                "requirement_description": "Fire clearance covering additional floors or buildings constructed for intake expansion.",
                "is_mandatory": True,
                "accepted_formats": "PDF, JPG, PNG",
                "required_fields": ["certificate_number", "expiry_date"],
                "validation_criteria": "Active validity date required.",
                "source_clause": "AICTE Approval Process Handbook (APH 2024–27), Chapter V, Section 5.4",
                "order_index": 3
            }
        ]
    }
}


class DocumentRequirementsEngine:
    def __init__(self, db: Session):
        self.db = db

    def seed_default_checklists(self):
        """Populate official APH 2024–27 checklists and requirements into database if absent."""
        for cat_key, cat_data in CHECKLIST_DEFINITIONS.items():
            checklist = self.db.query(ApplicationChecklist).filter(
                ApplicationChecklist.category == cat_key,
                ApplicationChecklist.academic_year == cat_data["academic_year"]
            ).first()

            if not checklist:
                checklist = ApplicationChecklist(
                    category=cat_key,
                    academic_year=cat_data["academic_year"],
                    title=cat_data["title"],
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                self.db.add(checklist)
                self.db.flush()

            # Seed requirements
            for req in cat_data["requirements"]:
                existing_req = self.db.query(ChecklistRequirement).filter(
                    ChecklistRequirement.checklist_id == checklist.id,
                    ChecklistRequirement.document_type == req["document_type"]
                ).first()

                if not existing_req:
                    rule_id_map = {
                        "FIRE_SAFETY_CERTIFICATE": 2,
                        "LAND_DOCUMENT": 1,
                        "LAND_DOCUMENTS": 1,
                        "LAND_USE_CERTIFICATE": 4,
                        "AFFILIATION_CERTIFICATE": 5,
                        "AFFILIATION_ORDER": 5,
                        "BUILDING_PLAN": 3,
                        "OCCUPANCY_CERTIFICATE": 3,
                        "AUDITED_FINANCIALS": 1,
                    }
                    target_rule_id = req.get("rule_id") or rule_id_map.get(req["document_type"], 1)

                    new_req = ChecklistRequirement(
                        checklist_id=checklist.id,
                        rule_id=target_rule_id,
                        document_type=req["document_type"],
                        requirement_title=req["requirement_title"],
                        requirement_description=req["requirement_description"],
                        is_mandatory=req["is_mandatory"],
                        accepted_formats=req["accepted_formats"],
                        required_fields=json.dumps(req["required_fields"]),
                        validation_criteria=req["validation_criteria"],
                        source_clause=req["source_clause"],
                        order_index=req["order_index"],
                        is_active=True
                    )
                    self.db.add(new_req)

        self.db.commit()

    def get_checklist_for_category(self, category: str, academic_year: str = "2025-2026") -> Optional[ApplicationChecklist]:
        """Fetch active checklist for category and academic cycle."""
        norm_cat = category.upper().strip()
        cl = self.db.query(ApplicationChecklist).filter(
            ApplicationChecklist.category == norm_cat,
            ApplicationChecklist.academic_year == academic_year,
            ApplicationChecklist.is_active == True
        ).first()

        if not cl:
            # Fallback to EXTENSION_OF_APPROVAL
            cl = self.db.query(ApplicationChecklist).filter(
                ApplicationChecklist.category == "EXTENSION_OF_APPROVAL",
                ApplicationChecklist.is_active == True
            ).first()

        return cl

    def evaluate_application_requirements(self, application_id: int) -> Dict[str, Any]:
        """
        Evaluate submitted documents against category-specific APH checklist.
        Identifies missing documents, missing required fields, expired certificates,
        unreadable files, and creates structured ApplicationDeficiency records.
        """
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # Ensure baseline checklists are present
        self.seed_default_checklists()

        cat_str = app.category.value if hasattr(app.category, "value") else str(app.category)
        checklist = self.get_checklist_for_category(cat_str, app.academic_year)
        if not checklist:
            return {"error": f"No checklist configured for category {cat_str}"}

        requirements = self.db.query(ChecklistRequirement).filter(
            ChecklistRequirement.checklist_id == checklist.id,
            ChecklistRequirement.is_active == True
        ).order_by(ChecklistRequirement.order_index.asc()).all()

        # Load submitted documents and their latest versions
        documents = self.db.query(Document).filter(Document.application_id == application_id).all()
        submitted_by_type: Dict[str, Document] = {}
        for d in documents:
            d_type = d.document_type.value if hasattr(d.document_type, "value") else str(d.document_type)
            submitted_by_type[d_type] = d
            # Map canonical equivalents
            if d_type in ("LAND_DOCUMENT", "LAND_DOCUMENTS", "LAND_USE_CERTIFICATE"):
                submitted_by_type.setdefault("LAND_DOCUMENT", d)
            elif d_type in ("AFFILIATION_CERTIFICATE", "AFFILIATION_ORDER"):
                submitted_by_type.setdefault("AFFILIATION_CERTIFICATE", d)
            elif d_type in ("AUDIT_STATEMENT", "AUDITED_FINANCIALS"):
                submitted_by_type.setdefault("AUDITED_FINANCIALS", d)

        checklist_results: List[Dict[str, Any]] = []
        new_deficiencies_created = 0
        deficiencies_resolved = 0
        outstanding_deficiencies: List[Dict[str, Any]] = []

        total_mandatory = sum(1 for r in requirements if r.is_mandatory)
        satisfied_mandatory = 0

        today = datetime.utcnow().date()

        for req in requirements:
            req_type = req.document_type
            req_fields = json.loads(req.required_fields or "[]")
            submitted_doc = submitted_by_type.get(req_type)

            latest_version: Optional[DocumentVersion] = None
            if submitted_doc:
                latest_version = self.db.query(DocumentVersion).filter(
                    DocumentVersion.document_id == submitted_doc.id
                ).order_by(DocumentVersion.version_number.desc()).first()

            item_status = "PENDING"
            deficiency_type: Optional[DeficiencyType] = None
            reason: Optional[str] = None
            required_action: Optional[str] = None
            missing_fields: List[str] = []

            # 1. Document Not Uploaded
            if not submitted_doc or not latest_version:
                if req.is_mandatory:
                    item_status = "MISSING"
                    deficiency_type = DeficiencyType.MISSING_MANDATORY_DOCUMENT
                    reason = f"Mandatory document '{req.requirement_title}' has not been uploaded for this {cat_str.replace('_', ' ').title()} application."
                    required_action = f"Upload the original {req.requirement_title} in accepted format ({req.accepted_formats})."
                else:
                    item_status = "NOT_SUBMITTED"

            # 2. Document Uploaded but Failed or Unreadable
            elif latest_version.status == ProcessingStatus.FAILED:
                item_status = "DEFICIENT"
                deficiency_type = DeficiencyType.UNREADABLE_CONTENT
                reason = f"Uploaded file '{latest_version.original_filename}' could not be processed: {latest_version.error_message or 'Corrupted file format'}."
                required_action = "Upload a clean, uncorrupted and readable copy."

            # 3. Document Uploaded — Evaluate Fields & Validity
            else:
                extracted_fields = {
                    f.field_key: f for f in self.db.query(ExtractedField).filter(
                        ExtractedField.document_version_id == latest_version.id
                    ).all()
                }

                # Check required fields
                for rf in req_fields:
                    if rf not in extracted_fields or not extracted_fields[rf].extracted_value:
                        missing_fields.append(rf)

                # Check validity / expiry date
                is_expired = False
                expiry_field = extracted_fields.get("expiry_date")
                if expiry_field:
                    try:
                        exp_val = expiry_field.normalized_value or expiry_field.extracted_value
                        exp_dt = datetime.strptime(exp_val, "%Y-%m-%d").date()
                        if exp_dt < today:
                            is_expired = True
                    except Exception:
                        pass

                if is_expired:
                    item_status = "EXPIRED"
                    deficiency_type = DeficiencyType.EXPIRED_DOCUMENT
                    reason = f"Uploaded certificate expired on {expiry_field.extracted_value}. Regulatory clearance must be active."
                    required_action = "Upload current renewed certificate from the issuing authority."
                elif missing_fields:
                    item_status = "MISSING_INFORMATION"
                    deficiency_type = DeficiencyType.MISSING_REQUIRED_FIELD
                    missing_labels = [f.replace("_", " ").title() for f in missing_fields]
                    reason = f"Required field(s) could not be extracted from '{latest_version.original_filename}': {', '.join(missing_labels)}."
                    required_action = f"Upload a clearer scan or record authorized field corrections."
                else:
                    item_status = "SATISFIED"
                    if req.is_mandatory:
                        satisfied_mandatory += 1

            # Manage Database Deficiency Record
            rule_code = f"DEF-{req_type}-{req.id}"
            existing_deficiency = self.db.query(ApplicationDeficiency).filter(
                ApplicationDeficiency.application_id == application_id,
                ApplicationDeficiency.rule_code == rule_code
            ).first()

            if deficiency_type:
                # Need an active deficiency
                if not existing_deficiency:
                    new_def = ApplicationDeficiency(
                        application_id=application_id,
                        rule_code=rule_code,
                        document_type=req_type,
                        deficiency_type=deficiency_type,
                        severity="CRITICAL" if req.is_mandatory else "MAJOR",
                        title=f"Deficiency: {req.requirement_title[:60]}",
                        description=req.requirement_description,
                        reason=reason or "Regulatory requirement shortfall detected.",
                        required_action=required_action or "Upload required document.",
                        responsible_party="INSTITUTION",
                        status=DeficiencyStatus.OPEN,
                        affected_document_version_id=latest_version.id if latest_version else None,
                        created_at=datetime.utcnow()
                    )
                    self.db.add(new_def)
                    new_deficiencies_created += 1
                    outstanding_deficiencies.append({
                        "title": new_def.title,
                        "reason": new_def.reason,
                        "required_action": new_def.required_action
                    })
                elif existing_deficiency.status == DeficiencyStatus.RESOLVED:
                    # Re-open if re-evaluated deficient
                    existing_deficiency.status = DeficiencyStatus.OPEN
                    existing_deficiency.reason = reason
                    existing_deficiency.required_action = required_action
                    existing_deficiency.affected_document_version_id = latest_version.id if latest_version else None
                    existing_deficiency.updated_at = datetime.utcnow()
                    outstanding_deficiencies.append({
                        "title": existing_deficiency.title,
                        "reason": existing_deficiency.reason,
                        "required_action": existing_deficiency.required_action
                    })
                else:
                    outstanding_deficiencies.append({
                        "title": existing_deficiency.title,
                        "reason": existing_deficiency.reason,
                        "required_action": existing_deficiency.required_action
                    })
            else:
                # Requirement is satisfied: if open deficiency exists, mark RESOLVED!
                if existing_deficiency and existing_deficiency.status == DeficiencyStatus.OPEN:
                    existing_deficiency.status = DeficiencyStatus.RESOLVED
                    existing_deficiency.resolved_by_document_version_id = latest_version.id if latest_version else None
                    existing_deficiency.resolution_notes = f"Satisfied by uploaded document version v{latest_version.version_number if latest_version else 1} ({latest_version.original_filename if latest_version else ''})."
                    existing_deficiency.resolved_at = datetime.utcnow()
                    deficiencies_resolved += 1

            checklist_results.append({
                "requirement_id": req.id,
                "document_type": req_type,
                "title": req.requirement_title,
                "description": req.requirement_description,
                "is_mandatory": req.is_mandatory,
                "accepted_formats": req.accepted_formats,
                "required_fields": req_fields,
                "validation_criteria": req.validation_criteria,
                "source_clause": req.source_clause,
                "status": item_status,
                "submitted_document_id": submitted_doc.id if submitted_doc else None,
                "latest_version_id": latest_version.id if latest_version else None,
                "latest_filename": latest_version.original_filename if latest_version else None,
                "latest_version_number": latest_version.version_number if latest_version else None,
                "ocr_status": latest_version.status.value if latest_version else None,
                "missing_fields": missing_fields,
                "reason": reason,
                "required_action": required_action
            })

        self.db.commit()

        # Send institutional notification if new deficiencies were identified
        target_user_id = app.submitting_user_id
        if not target_user_id and app.institution_id:
            membership = self.db.query(InstitutionMembership).filter(
                InstitutionMembership.institution_id == app.institution_id
            ).first()
            if membership:
                target_user_id = membership.user_id

        if new_deficiencies_created > 0 and target_user_id:
            bullet_items = "\n".join([f"• {d['title']}: {d['required_action']}" for d in outstanding_deficiencies[:5]])
            notif_msg = (
                f"Regulatory document scrutiny identified {len(outstanding_deficiencies)} outstanding requirement(s) "
                f"for Application {app.reference_no} ({cat_str.replace('_', ' ').title()}):\n\n"
                f"{bullet_items}\n\n"
                f"Please open your Application Workspace, upload the requested documents, and resubmit."
            )
            create_notification(
                db=self.db,
                user_id=target_user_id,
                title=f"Additional Documents Required — {app.reference_no}",
                message=notif_msg,
                notification_type="WARNING",
                link=f"/applications/{app.id}"
            )

        completion_pct = round((satisfied_mandatory / max(1, total_mandatory)) * 100, 1)
        can_submit = (satisfied_mandatory == total_mandatory)

        return {
            "application_id": application_id,
            "reference_no": app.reference_no,
            "category": cat_str,
            "checklist_title": checklist.title,
            "academic_year": checklist.academic_year,
            "total_requirements": len(requirements),
            "mandatory_requirements": total_mandatory,
            "satisfied_mandatory": satisfied_mandatory,
            "completion_percentage": completion_pct,
            "can_submit": can_submit,
            "open_deficiencies_count": len(outstanding_deficiencies),
            "items": checklist_results
        }

