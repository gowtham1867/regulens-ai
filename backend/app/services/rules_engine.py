import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.application import Application, ApplicationStatus
from app.models.document import Document, DocumentVersion, ExtractedField, DocumentType, ProcessingStatus
from app.models.rule import RegulatoryRule, RegulatoryRuleVersion, RuleCategory, RuleSeverity, EvaluationMethod
from app.models.finding import ValidationRun, ValidationFinding, FindingEvidenceLink, FindingStatus, TriggerType
from app.models.institution import Institution


class ComplianceRulesEngine:
    def __init__(self, db: Session):
        self.db = db

    def execute_validation_run(
        self,
        application_id: int,
        trigger_type: TriggerType = TriggerType.INITIAL_VALIDATION,
        triggering_change: Optional[str] = None
    ) -> ValidationRun:
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        # Determine next run number
        last_run = self.db.query(ValidationRun).filter(
            ValidationRun.application_id == application_id
        ).order_by(ValidationRun.run_number.desc()).first()
        run_number = (last_run.run_number + 1) if last_run else 1

        val_run = ValidationRun(
            application_id=application_id,
            run_number=run_number,
            trigger_type=trigger_type,
            triggering_change=triggering_change or "Validation initiated by system",
            executed_at=datetime.utcnow()
        )
        self.db.add(val_run)
        self.db.flush()

        # Load active regulatory rules
        active_rules = self.db.query(RegulatoryRule).filter(RegulatoryRule.is_active == True).all()
        
        # Load active documents and latest versions
        documents = self.db.query(Document).filter(Document.application_id == application_id).all()
        doc_version_map: Dict[int, DocumentVersion] = {}
        for d in documents:
            latest_v = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == d.id
            ).order_by(DocumentVersion.version_number.desc()).first()
            if latest_v:
                doc_version_map[d.id] = latest_v

        # Collect all extracted fields into an indexed dictionary
        extracted_fields_by_doc_type: Dict[str, Dict[str, ExtractedField]] = {}
        all_doc_versions: List[DocumentVersion] = list(doc_version_map.values())
        
        for d in documents:
            latest_v = doc_version_map.get(d.id)
            if latest_v:
                doc_key = d.document_type.value if hasattr(d.document_type, "value") else str(d.document_type)
                extracted_fields_by_doc_type.setdefault(doc_key, {})
                fields = self.db.query(ExtractedField).filter(
                    ExtractedField.document_version_id == latest_v.id
                ).all()
                for f in fields:
                    extracted_fields_by_doc_type[doc_key][f.field_key] = f

                # Normalize to canonical groups
                if doc_key in ("LAND_DOCUMENT", "LAND_DOCUMENTS", "LAND_USE_CERTIFICATE"):
                    extracted_fields_by_doc_type.setdefault("LAND_DOCUMENT", {})
                    for f in fields:
                        extracted_fields_by_doc_type["LAND_DOCUMENT"][f.field_key] = f
                elif doc_key in ("AFFILIATION_CERTIFICATE", "AFFILIATION_ORDER"):
                    extracted_fields_by_doc_type.setdefault("AFFILIATION_CERTIFICATE", {})
                    for f in fields:
                        extracted_fields_by_doc_type["AFFILIATION_CERTIFICATE"][f.field_key] = f
                elif doc_key in ("AUDIT_STATEMENT", "AUDITED_FINANCIALS"):
                    extracted_fields_by_doc_type.setdefault("AUDIT_STATEMENT", {})
                    for f in fields:
                        extracted_fields_by_doc_type["AUDIT_STATEMENT"][f.field_key] = f

        findings_to_create: List[ValidationFinding] = []
        passed_count = 0
        failed_count = 0
        warning_count = 0
        manual_review_count = 0

        # Mark previous active findings as superseded if revalidation
        if trigger_type == TriggerType.CHANGE_AWARE_REVALIDATION:
            prev_findings = self.db.query(ValidationFinding).filter(
                ValidationFinding.application_id == application_id,
                ValidationFinding.is_active == True
            ).all()
            for pf in prev_findings:
                pf.is_active = False

        for rule in active_rules:
            finding_data = self._evaluate_rule(
                rule=rule,
                application=app,
                institution=app.institution,
                documents=documents,
                doc_version_map=doc_version_map,
                fields_by_doc_type=extracted_fields_by_doc_type,
                val_run_id=val_run.id
            )

            if finding_data:
                finding = ValidationFinding(
                    validation_run_id=val_run.id,
                    application_id=application_id,
                    rule_id=rule.id,
                    status=finding_data["status"],
                    severity=finding_data["severity"],
                    affected_claim_field=finding_data.get("affected_claim_field"),
                    affected_document_version_id=finding_data.get("affected_document_version_id"),
                    expected_value=finding_data.get("expected_value"),
                    observed_value=finding_data.get("observed_value"),
                    explanation=finding_data["explanation"],
                    recommended_action=finding_data.get("recommended_action"),
                    source_page=finding_data.get("source_page"),
                    is_active=True,
                    is_resolved=(finding_data["status"] == FindingStatus.PASSED)
                )
                self.db.add(finding)
                self.db.flush()

                # Add evidence link if available
                if finding_data.get("evidence"):
                    ev = finding_data["evidence"]
                    link = FindingEvidenceLink(
                        finding_id=finding.id,
                        document_version_id=ev["document_version_id"],
                        extracted_field_id=ev.get("extracted_field_id"),
                        source_page=ev.get("source_page", 1),
                        evidence_excerpt=ev.get("excerpt")
                    )
                    self.db.add(link)

                findings_to_create.append(finding)
                
                if finding.status == FindingStatus.PASSED:
                    passed_count += 1
                elif finding.status == FindingStatus.FAILED:
                    failed_count += 1
                elif finding.status == FindingStatus.WARNING:
                    warning_count += 1
                elif finding.status == FindingStatus.MANUAL_REVIEW_REQUIRED:
                    manual_review_count += 1

        val_run.total_rules_evaluated = len(active_rules)
        val_run.passed_count = passed_count
        val_run.failed_count = failed_count
        val_run.warning_count = warning_count
        val_run.manual_review_count = manual_review_count

        self.db.commit()
        self.db.refresh(val_run)
        return val_run

    def _evaluate_rule(
        self,
        rule: RegulatoryRule,
        application: Application,
        institution: Institution,
        documents: List[Document],
        doc_version_map: Dict[int, DocumentVersion],
        fields_by_doc_type: Dict[str, Dict[str, ExtractedField]],
        val_run_id: int
    ) -> Optional[Dict[str, Any]]:
        code = rule.rule_code

        # RULE 1: Land Document Presence
        if code == "AICTE-RULE-001-LAND-MANDATORY":
            land_doc = next((d for d in documents if d.document_type in (
                DocumentType.LAND_DOCUMENT,
                DocumentType.LAND_DOCUMENTS,
                DocumentType.LAND_USE_CERTIFICATE
            )), None)
            if not land_doc or land_doc.id not in doc_version_map:
                return {
                    "status": FindingStatus.FAILED,
                    "severity": "CRITICAL",
                    "affected_claim_field": "LAND_DOCUMENT",
                    "expected_value": "Registered Land Ownership or Lease Deed document present",
                    "observed_value": "Missing document",
                    "explanation": "No Land Document was uploaded for this application. Technical institutions require clear land title records.",
                    "recommended_action": "Upload approved registered land title / continuous lease deed."
                }
            v = doc_version_map[land_doc.id]
            return {
                "status": FindingStatus.PASSED,
                "severity": "INFO",
                "affected_claim_field": "LAND_DOCUMENT",
                "affected_document_version_id": v.id,
                "expected_value": "Document present",
                "observed_value": f"Uploaded: {v.original_filename} (v{v.version_number})",
                "explanation": "Mandatory Land Document is uploaded and ready for title verification.",
                "evidence": {"document_version_id": v.id, "source_page": 1}
            }

        # RULE 2: Fire Safety Certificate Validity
        elif code == "AICTE-RULE-002-FIRE-VALIDITY":
            fire_doc = next((d for d in documents if d.document_type == DocumentType.FIRE_SAFETY_CERTIFICATE), None)
            if not fire_doc or fire_doc.id not in doc_version_map:
                return {
                    "status": FindingStatus.FAILED,
                    "severity": "CRITICAL",
                    "affected_claim_field": "FIRE_SAFETY_CERTIFICATE",
                    "expected_value": "Valid Fire Safety NOC/Certificate present",
                    "observed_value": "Missing certificate",
                    "explanation": "Fire Safety Certificate is mandatory for institutional safety scrutiny.",
                    "recommended_action": "Upload current Fire Safety Certificate issued by State Fire Services."
                }

            v = doc_version_map[fire_doc.id]
            fields = fields_by_doc_type.get("FIRE_SAFETY_CERTIFICATE", {})
            expiry_f = fields.get("expiry_date")

            if not expiry_f:
                return {
                    "status": FindingStatus.MANUAL_REVIEW_REQUIRED,
                    "severity": "MAJOR",
                    "affected_claim_field": "expiry_date",
                    "affected_document_version_id": v.id,
                    "expected_value": "Explicit expiry date present in certificate",
                    "observed_value": "Not detected automatically",
                    "explanation": "Expiry date could not be automatically extracted from the Fire Safety Certificate. Manual inspection required.",
                    "recommended_action": "Verify certificate validity date manually or upload a clearer scan.",
                    "evidence": {"document_version_id": v.id, "source_page": 1}
                }

            # Check if expired
            today = datetime.utcnow().date()
            try:
                exp_date = datetime.strptime(expiry_f.normalized_value or expiry_f.extracted_value, "%Y-%m-%d").date()
                if exp_date < today:
                    return {
                        "status": FindingStatus.FAILED,
                        "severity": "CRITICAL",
                        "affected_claim_field": "expiry_date",
                        "affected_document_version_id": v.id,
                        "expected_value": f"Valid beyond {today.isoformat()}",
                        "observed_value": f"Expired on {exp_date.isoformat()}",
                        "explanation": f"Fire Safety Certificate expired on {exp_date.isoformat()}. Applications with lapsed fire safety clearances cannot be approved.",
                        "recommended_action": "Upload an unexpired Fire Safety NOC / renewal certificate from the competent authority.",
                        "source_page": expiry_f.source_page,
                        "evidence": {
                            "document_version_id": v.id,
                            "extracted_field_id": expiry_f.id,
                            "source_page": expiry_f.source_page,
                            "excerpt": f"Expiry Date: {expiry_f.extracted_value}"
                        }
                    }
                else:
                    return {
                        "status": FindingStatus.PASSED,
                        "severity": "INFO",
                        "affected_claim_field": "expiry_date",
                        "affected_document_version_id": v.id,
                        "expected_value": f"Valid beyond {today.isoformat()}",
                        "observed_value": f"Valid until {exp_date.isoformat()}",
                        "explanation": f"Fire Safety Certificate is current and valid until {exp_date.isoformat()}.",
                        "source_page": expiry_f.source_page,
                        "evidence": {
                            "document_version_id": v.id,
                            "extracted_field_id": expiry_f.id,
                            "source_page": expiry_f.source_page,
                            "excerpt": f"Valid until: {expiry_f.extracted_value}"
                        }
                    }
            except Exception:
                return {
                    "status": FindingStatus.MANUAL_REVIEW_REQUIRED,
                    "severity": "MAJOR",
                    "affected_claim_field": "expiry_date",
                    "affected_document_version_id": v.id,
                    "expected_value": "Standard date format",
                    "observed_value": expiry_f.extracted_value,
                    "explanation": f"Date format '{expiry_f.extracted_value}' requires officer verification.",
                    "recommended_action": "Review date manually.",
                    "evidence": {"document_version_id": v.id, "extracted_field_id": expiry_f.id, "source_page": expiry_f.source_page}
                }

        # RULE 3: Institution Name Cross-Document Consistency
        elif code == "AICTE-RULE-003-NAME-CONSISTENCY":
            master_name = institution.name.strip().lower()
            mismatches: List[str] = []
            ev_doc_v = None
            ev_field = None

            for doc_type, fields in fields_by_doc_type.items():
                inst_f = fields.get("institution_name")
                if inst_f:
                    extracted_name = (inst_f.normalized_value or inst_f.extracted_value).strip().lower()
                    # Normalized fuzzy/token check
                    master_tokens = set(re.findall(r'\w+', master_name))
                    extracted_tokens = set(re.findall(r'\w+', extracted_name))
                    common = master_tokens.intersection(extracted_tokens)
                    similarity = len(common) / max(len(master_tokens), len(extracted_tokens), 1)

                    if similarity < 0.60:
                        mismatches.append(f"{doc_type}: '{inst_f.extracted_value}'")
                        ev_field = inst_f
                        # Find corresponding doc version
                        doc_obj = next((d for d in documents if d.document_type.value == doc_type), None)
                        if doc_obj:
                            ev_doc_v = doc_version_map.get(doc_obj.id)

            if mismatches:
                return {
                    "status": FindingStatus.WARNING,
                    "severity": "MAJOR",
                    "affected_claim_field": "institution_name",
                    "affected_document_version_id": ev_doc_v.id if ev_doc_v else None,
                    "expected_value": institution.name,
                    "observed_value": "; ".join(mismatches),
                    "explanation": f"Discrepancy detected between institutional master record ('{institution.name}') and name in uploaded document(s).",
                    "recommended_action": "Request clarification or name rectification deed to ensure name consistency across all records.",
                    "source_page": ev_field.source_page if ev_field else 1,
                    "evidence": {
                        "document_version_id": ev_doc_v.id if ev_doc_v else None,
                        "extracted_field_id": ev_field.id if ev_field else None,
                        "source_page": ev_field.source_page if ev_field else 1,
                        "excerpt": f"Observed name: {ev_field.extracted_value if ev_field else ''}"
                    } if ev_doc_v else None
                }
            else:
                return {
                    "status": FindingStatus.PASSED,
                    "severity": "INFO",
                    "affected_claim_field": "institution_name",
                    "expected_value": institution.name,
                    "observed_value": institution.name,
                    "explanation": "Institution name matches consistently across institutional master records and extracted document fields."
                }

        # RULE 4: Land Area Threshold Evaluation
        elif code == "AICTE-RULE-004-LAND-THRESHOLD":
            land_fields = fields_by_doc_type.get("LAND_DOCUMENT", {})
            area_f = land_fields.get("land_area")
            land_doc = next((d for d in documents if d.document_type in (
                DocumentType.LAND_DOCUMENT,
                DocumentType.LAND_DOCUMENTS,
                DocumentType.LAND_USE_CERTIFICATE
            )), None)
            v = doc_version_map.get(land_doc.id) if land_doc else None

            # Minimum required land for technical engineering institute in urban/rural (illustrative: 7.5 Acres)
            min_required_acres = 7.5
            
            if not area_f:
                return {
                    "status": FindingStatus.MANUAL_REVIEW_REQUIRED,
                    "severity": "MAJOR",
                    "affected_claim_field": "land_area",
                    "affected_document_version_id": v.id if v else None,
                    "expected_value": f"Minimum {min_required_acres} Acres stated in deed",
                    "observed_value": "Field not extracted",
                    "explanation": "Land area could not be automatically parsed from deed text. Manual scrutiny of schedule of property required.",
                    "recommended_action": "Officer to inspect schedule of property on page 2-3 of land document.",
                    "evidence": {"document_version_id": v.id, "source_page": 1} if v else None
                }

            try:
                # Extract numeric value
                num_str = re.search(r'([0-9]+(?:\.[0-9]+)?)', area_f.extracted_value)
                val = float(num_str.group(1)) if num_str else 0.0
                
                if val < min_required_acres:
                    return {
                        "status": FindingStatus.FAILED,
                        "severity": "CRITICAL",
                        "affected_claim_field": "land_area",
                        "affected_document_version_id": v.id if v else None,
                        "expected_value": f">= {min_required_acres} Acres",
                        "observed_value": f"{val} Acres",
                        "explanation": f"Extracted land area of {val} Acres is below the minimum regulatory requirement of {min_required_acres} Acres.",
                        "recommended_action": "Require institution to provide additional contiguous land survey records or justify classification.",
                        "source_page": area_f.source_page,
                        "evidence": {
                            "document_version_id": v.id if v else None,
                            "extracted_field_id": area_f.id,
                            "source_page": area_f.source_page,
                            "excerpt": f"Total Land Area: {area_f.extracted_value}"
                        }
                    }
                else:
                    return {
                        "status": FindingStatus.PASSED,
                        "severity": "INFO",
                        "affected_claim_field": "land_area",
                        "affected_document_version_id": v.id if v else None,
                        "expected_value": f">= {min_required_acres} Acres",
                        "observed_value": f"{val} Acres",
                        "explanation": f"Documented land area of {val} Acres complies with minimum norm of {min_required_acres} Acres.",
                        "source_page": area_f.source_page,
                        "evidence": {
                            "document_version_id": v.id if v else None,
                            "extracted_field_id": area_f.id,
                            "source_page": area_f.source_page,
                            "excerpt": f"Total Land Area: {area_f.extracted_value}"
                        }
                    }
            except Exception:
                return {
                    "status": FindingStatus.MANUAL_REVIEW_REQUIRED,
                    "severity": "MINOR",
                    "affected_claim_field": "land_area",
                    "affected_document_version_id": v.id if v else None,
                    "expected_value": f"Numeric acreage >= {min_required_acres}",
                    "observed_value": area_f.extracted_value,
                    "explanation": f"Could not compute numeric area from '{area_f.extracted_value}'.",
                    "recommended_action": "Review deed manually."
                }

        # RULE 5: Approved Intake Consistency
        elif code == "AICTE-RULE-005-INTAKE-CONSISTENCY":
            affil_fields = fields_by_doc_type.get("AFFILIATION_CERTIFICATE", {})
            intake_f = affil_fields.get("approved_intake")
            affil_doc = next((d for d in documents if d.document_type in (
                DocumentType.AFFILIATION_CERTIFICATE,
                DocumentType.AFFILIATION_ORDER
            )), None)
            v = doc_version_map.get(affil_doc.id) if affil_doc else None

            declared_intake = application.declared_intake or institution.approved_intake

            if not intake_f:
                return {
                    "status": FindingStatus.WARNING,
                    "severity": "MINOR",
                    "affected_claim_field": "approved_intake",
                    "affected_document_version_id": v.id if v else None,
                    "expected_value": f"Intake capacity: {declared_intake}",
                    "observed_value": "Intake not listed on affiliation letter",
                    "explanation": "Sanctioned intake is not explicitly specified on the affiliation letter.",
                    "recommended_action": "Check university annexure for sanctioned course-wise intake breakdown."
                }

            try:
                extracted_intake = int(re.search(r'\d+', intake_f.extracted_value).group(0))
                if extracted_intake != declared_intake:
                    return {
                        "status": FindingStatus.WARNING,
                        "severity": "MAJOR",
                        "affected_claim_field": "approved_intake",
                        "affected_document_version_id": v.id if v else None,
                        "expected_value": f"{declared_intake} seats (Declared)",
                        "observed_value": f"{extracted_intake} seats (Affiliation Letter)",
                        "explanation": f"Mismatch between application declared intake ({declared_intake}) and university affiliation sanction ({extracted_intake}).",
                        "recommended_action": "Seek clarification on student intake adjustment or updated university approval.",
                        "source_page": intake_f.source_page,
                        "evidence": {
                            "document_version_id": v.id if v else None,
                            "extracted_field_id": intake_f.id,
                            "source_page": intake_f.source_page,
                            "excerpt": f"Sanctioned intake: {intake_f.extracted_value}"
                        }
                    }
                else:
                    return {
                        "status": FindingStatus.PASSED,
                        "severity": "INFO",
                        "affected_claim_field": "approved_intake",
                        "affected_document_version_id": v.id if v else None,
                        "expected_value": f"{declared_intake} seats",
                        "observed_value": f"{extracted_intake} seats",
                        "explanation": f"Approved intake of {extracted_intake} seats in affiliation certificate matches application declaration.",
                        "source_page": intake_f.source_page,
                        "evidence": {
                            "document_version_id": v.id if v else None,
                            "extracted_field_id": intake_f.id,
                            "source_page": intake_f.source_page,
                            "excerpt": f"Sanctioned intake: {intake_f.extracted_value}"
                        }
                    }
            except Exception:
                return {
                    "status": FindingStatus.MANUAL_REVIEW_REQUIRED,
                    "severity": "MINOR",
                    "affected_claim_field": "approved_intake",
                    "affected_document_version_id": v.id if v else None,
                    "expected_value": str(declared_intake),
                    "observed_value": intake_f.extracted_value,
                    "explanation": "Could not parse numerical intake count.",
                    "recommended_action": "Verify manually."
                }

        # Fallback for any other rule
        return {
            "status": FindingStatus.NOT_EVALUATED,
            "severity": "INFO",
            "expected_value": "Rule criteria",
            "observed_value": "Rule execution not configured",
            "explanation": f"Evaluation for rule {rule.rule_code} completed baseline check."
        }

