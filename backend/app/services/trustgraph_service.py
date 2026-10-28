from typing import Dict, Any, List, Set, Optional
from sqlalchemy.orm import Session
from app.models.application import Application
from app.models.document import Document, DocumentVersion, ExtractedField
from app.models.finding import ValidationFinding
from app.models.verification import VerificationAttempt
from app.models.workflow import OfficerReview, WorkflowDecision
from app.models.deficiency import ApplicationDeficiency, DeficiencyStatus
from app.models.duplicate import DuplicateRecord, DuplicateStatus
from app.models.rule import ChecklistRequirement


class TrustGraphService:
    def __init__(self, db: Session):
        self.db = db

    def generate_graph_for_application(self, application_id: int) -> Dict[str, Any]:
        app = self.db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application {application_id} not found")

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        seen_nodes: Set[str] = set()
        finding_paths: Dict[str, List[str]] = {}

        def add_node(
            node_id: str,
            label: str,
            node_type: str,
            tier: int,
            status: str = "DEFAULT",
            metadata: Optional[Dict[str, Any]] = None
        ):
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                nodes.append({
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "tier": tier,
                    "status": status,
                    "metadata": metadata or {}
                })

        def add_edge(
            source_id: str,
            target_id: str,
            label: str,
            edge_type: str = "DEFAULT",
            confidence: float = 1.0
        ):
            edges.append({
                "source": source_id,
                "target": target_id,
                "label": label,
                "type": edge_type,
                "confidence": confidence
            })

        def to_str(val):
            if val is None:
                return ""
            return val.value if hasattr(val, "value") else str(val)

        # =========================================================================
        # TIER 0: INSTITUTION / BASELINE
        # =========================================================================
        inst = app.institution
        inst_node_id = f"inst_{inst.id}"
        add_node(
            node_id=inst_node_id,
            label=inst.name,
            node_type="INSTITUTION",
            tier=0,
            status="VERIFIED",
            metadata={
                "aicte_id": inst.aicte_id,
                "state": inst.state,
                "district": inst.district,
                "institution_type": inst.institution_type,
                "approved_intake": inst.approved_intake,
                "land_area": f"{inst.land_area_acres} Acres"
            }
        )

        # Baseline Land & Intake nodes
        baseline_land_node_id = f"baseline_land_{inst.id}"
        add_node(
            node_id=baseline_land_node_id,
            label=f"Baseline Land: {inst.land_area_acres} Acres",
            node_type="BASELINE_RECORD",
            tier=0,
            status="VERIFIED",
            metadata={
                "metric": "LAND_AREA_ACRES",
                "established_value": inst.land_area_acres,
                "authority": "AICTE_MASTER_RECORD"
            }
        )
        add_edge(inst_node_id, baseline_land_node_id, "ESTABLISHED_BASELINE", "BASELINE", 1.0)

        # =========================================================================
        # TIER 1: APPLICATION & DECLARED CLAIMS
        # =========================================================================
        app_node_id = f"app_{app.id}"
        add_node(
            node_id=app_node_id,
            label=f"App {app.reference_no}",
            node_type="APPLICATION",
            tier=1,
            status=to_str(app.status),
            metadata={
                "reference_no": app.reference_no,
                "category": to_str(app.category),
                "academic_year": app.academic_year,
                "declared_intake": app.declared_intake,
                "declared_land": f"{app.declared_land_acres} Acres",
                "submission_date": app.created_at.strftime("%Y-%m-%d") if app.created_at else "N/A"
            }
        )
        add_edge(app_node_id, inst_node_id, "SUBMITTED_WITH", "ORGANIZATIONAL", 1.0)

        # Claims Nodes (Declared by College)
        for claim in app.claims:
            claim_node_id = f"claim_{claim.id}"
            add_node(
                node_id=claim_node_id,
                label=f"Claim: {claim.field_name}",
                node_type="CLAIM",
                tier=1,
                status="DECLARED",
                metadata={
                    "field_name": claim.field_name,
                    "declared_value": claim.declared_value,
                    "claim_type": claim.claim_type
                }
            )
            add_edge(app_node_id, claim_node_id, "DECLARES", "CLAIM_RELATION", 1.0)

        # Checklist Requirements Nodes
        from app.services.document_requirements_service import DocumentRequirementsEngine
        req_engine = DocumentRequirementsEngine(self.db)
        cat_str = to_str(app.category)
        cl = req_engine.get_checklist_for_category(cat_str, app.academic_year)
        if cl:
            for req in cl.requirements:
                req_node_id = f"req_{req.id}"
                add_node(
                    node_id=req_node_id,
                    label=f"Req: {(req.requirement_title or req.document_type)[:28]}",
                    node_type="CHECKLIST_REQUIREMENT",
                    tier=1,
                    status="MANDATORY" if req.is_mandatory else "CONDITIONAL",
                    metadata={
                        "title": req.requirement_title,
                        "document_type": req.document_type,
                        "is_mandatory": req.is_mandatory,
                        "source_clause": req.source_clause
                    }
                )
                add_edge(app_node_id, req_node_id, "REQUIRES_CHECKLIST_DOC", "GOVERNANCE", 1.0)

        # =========================================================================
        # TIER 2: DOCUMENTS & EVIDENCE
        # =========================================================================
        docs = self.db.query(Document).filter(Document.application_id == application_id).all()
        doc_node_map = {}
        version_doc_map = {}

        for doc in docs:
            doc_node_id = f"doc_{doc.id}"
            doc_node_map[doc.id] = doc_node_id

            latest_v = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == doc.id
            ).order_by(DocumentVersion.version_number.desc()).first()

            if latest_v:
                version_doc_map[latest_v.id] = doc_node_id

            v_info = f"v{latest_v.version_number}" if latest_v else "No File"
            add_node(
                node_id=doc_node_id,
                label=f"{doc.title} ({v_info})",
                node_type="DOCUMENT",
                tier=2,
                status=to_str(latest_v.status) if latest_v else "PENDING",
                metadata={
                    "document_type": to_str(doc.document_type),
                    "title": doc.title,
                    "filename": latest_v.original_filename if latest_v else "N/A",
                    "file_hash": latest_v.file_hash if latest_v else "N/A",
                    "version_number": latest_v.version_number if latest_v else 0,
                    "page_count": latest_v.page_count if latest_v else 0,
                    "ocr_confidence": f"{int((latest_v.ocr_confidence or 0.85) * 100)}%" if latest_v else "0%"
                }
            )
            add_edge(doc_node_id, app_node_id, "BELONGS_TO", "EVIDENCE_PROVENANCE", 1.0)

        # =========================================================================
        # TIER 3: EXTRACTED FIELDS & ISSUER VERIFICATIONS
        # =========================================================================
        field_node_map = {}
        all_extracted_claims = []

        for doc in docs:
            doc_node_id = doc_node_map[doc.id]
            versions = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == doc.id
            ).order_by(DocumentVersion.version_number.asc()).all()

            for v in versions:
                fields = self.db.query(ExtractedField).filter(
                    ExtractedField.document_version_id == v.id
                ).all()

                for field in fields:
                    field_node_id = f"field_{field.id}"
                    field_node_map[field.id] = field_node_id

                    field_status = "CORRECTED" if field.is_manually_corrected else (
                        "HIGH_CONFIDENCE" if (field.confidence or 0.9) >= 0.85 else "LOW_CONFIDENCE"
                    )

                    disp_val = field.corrected_value if field.is_manually_corrected else field.extracted_value

                    add_node(
                        node_id=field_node_id,
                        label=f"{field.field_label}: {disp_val}",
                        node_type="EXTRACTED_FIELD",
                        tier=3,
                        status=field_status,
                        metadata={
                            "field_key": field.field_key,
                            "field_label": field.field_label,
                            "extracted_value": field.extracted_value,
                            "normalized_value": field.normalized_value or field.extracted_value,
                            "confidence": f"{int((field.confidence or 0.9) * 100)}%",
                            "source_page": field.source_page,
                            "is_corrected": field.is_manually_corrected,
                            "document_title": doc.title,
                            "version": f"v{v.version_number}"
                        }
                    )

                    add_edge(
                        source_id=field_node_id,
                        target_id=doc_node_id,
                        label="EXTRACTED_FROM",
                        edge_type="DATA_PROVENANCE",
                        confidence=field.confidence or 0.9
                    )

                    all_extracted_claims.append({
                        "field_id": field.id,
                        "document_id": doc.id,
                        "document_title": doc.title,
                        "document_type": doc.document_type.value,
                        "version": f"v{v.version_number}",
                        "field_key": field.field_key,
                        "field_label": field.field_label,
                        "extracted_value": field.extracted_value,
                        "normalized_value": field.normalized_value or field.extracted_value,
                        "confidence": round((field.confidence or 0.9) * 100, 1),
                        "source_page": field.source_page,
                        "is_manually_corrected": field.is_manually_corrected,
                        "corrected_value": field.corrected_value,
                        "correction_reason": field.correction_reason
                    })

                # Verification Attempts for this version
                attempts = self.db.query(VerificationAttempt).filter(
                    VerificationAttempt.document_version_id == v.id
                ).all()

                for att in attempts:
                    att_node_id = f"verify_{att.id}"
                    outcome_str = to_str(att.outcome)
                    add_node(
                        node_id=att_node_id,
                        label=f"Verified: {att.source.name}",
                        node_type="VERIFICATION",
                        tier=3,
                        status=outcome_str,
                        metadata={
                            "authority": att.source.name,
                            "authority_type": to_str(getattr(att.source, "authority_type", "GOVERNMENT_PORTAL")),
                            "outcome": outcome_str,
                            "is_simulated": att.is_simulated,
                            "is_reused": att.is_reused,
                            "method": to_str(att.verification_method),
                            "certificate_number": att.certificate_number,
                            "failure_reason": att.failure_reason
                        }
                    )
                    add_edge(
                        source_id=att_node_id,
                        target_id=doc_node_id,
                        label="VERIFIED_AGAINST",
                        edge_type="AUTHORITATIVE_VERIFICATION",
                        confidence=1.0 if outcome_str == "SUCCESS" else 0.4
                    )

        # =========================================================================
        # TIER 4: FINDINGS, RULES & DECISIONS
        # =========================================================================
        findings = self.db.query(ValidationFinding).filter(
            ValidationFinding.application_id == application_id,
            ValidationFinding.is_active == True
        ).all()

        for f in findings:
            finding_node_id = f"finding_{f.id}"
            status_val = to_str(f.status)
            f_status = "DEFICIENT" if status_val in ["FAIL", "CRITICAL", "FAILED"] else status_val

            add_node(
                node_id=finding_node_id,
                label=f"Finding: {f.rule.rule_code}",
                node_type="FINDING",
                tier=4,
                status=f_status,
                metadata={
                    "rule_code": f.rule.rule_code,
                    "severity": f.severity,
                    "rule_title": f.rule.title,
                    "expected": f.expected_value,
                    "observed": f.observed_value,
                    "explanation": f.explanation,
                    "recommended_action": f.recommended_action
                }
            )

            # Rule Node
            rule_node_id = f"rule_{f.rule.id}"
            add_node(
                node_id=rule_node_id,
                label=f"Rule: {f.rule.title}",
                node_type="REGULATORY_RULE",
                tier=4,
                status="ACTIVE",
                metadata={
                    "code": f.rule.rule_code,
                    "category": to_str(f.rule.category),
                    "severity": to_str(f.rule.severity),
                    "is_illustrative": f.rule.is_illustrative,
                    "source": f.rule.official_source_ref
                }
            )

            add_edge(finding_node_id, rule_node_id, "EVALUATED_BY_RULE", "RULE_GOVERNANCE", 1.0)
            add_edge(finding_node_id, app_node_id, "SUPPORTS_FINDING", "FINDING_PROVENANCE", 1.0)

            # Trace backward provenance path for finding
            path_nodes = [finding_node_id, rule_node_id, app_node_id, inst_node_id]

            # Connect finding to affected document and fields
            if f.affected_document_version_id and f.affected_document_version_id in version_doc_map:
                target_doc_node_id = version_doc_map[f.affected_document_version_id]
                add_edge(finding_node_id, target_doc_node_id, "EVALUATES_EVIDENCE", "EVIDENCE_LINK", 1.0)
                path_nodes.append(target_doc_node_id)

                # Connect to extracted fields under this document
                related_fields = self.db.query(ExtractedField).filter(
                    ExtractedField.document_version_id == f.affected_document_version_id
                ).all()
                for rf in related_fields:
                    if rf.id in field_node_map:
                        f_node_id = field_node_map[rf.id]
                        add_edge(finding_node_id, f_node_id, "SUPPORTS_FINDING", "FIELD_EVIDENCE", 1.0)
                        path_nodes.append(f_node_id)

            finding_paths[str(f.id)] = list(set(path_nodes))

        # Deficiencies Nodes (Tier 4)
        deficiencies = self.db.query(ApplicationDeficiency).filter(
            ApplicationDeficiency.application_id == application_id,
            ApplicationDeficiency.status == DeficiencyStatus.OPEN
        ).all()
        for df in deficiencies:
            def_node_id = f"def_{df.id}"
            add_node(
                node_id=def_node_id,
                label=f"Deficiency: {df.title[:30]}",
                node_type="DEFICIENCY",
                tier=4,
                status="DEFICIENT",
                metadata={
                    "deficiency_type": to_str(df.deficiency_type),
                    "severity": df.severity,
                    "reason": df.reason,
                    "required_action": df.required_action
                }
            )
            add_edge(def_node_id, app_node_id, "APPLICATION_DEFICIENCY", "DEFICIENCY_LINK", 1.0)
            if df.affected_document_version_id and df.affected_document_version_id in version_doc_map:
                target_doc_id = version_doc_map[df.affected_document_version_id]
                add_edge(def_node_id, target_doc_id, "IDENTIFIED_IN_DOCUMENT", "DEFICIENCY_EVIDENCE", 1.0)

        # Duplicate Records Nodes (Tier 2)
        dup_records = self.db.query(DuplicateRecord).filter(
            DuplicateRecord.application_id == application_id
        ).all()
        for dr in dup_records:
            if dr.document_version_id in version_doc_map:
                doc_node = version_doc_map[dr.document_version_id]
                dup_node_id = f"dup_{dr.id}"
                add_node(
                    node_id=dup_node_id,
                    label=f"Duplicate: {to_str(dr.match_type)}",
                    node_type="DUPLICATE_FLAG",
                    tier=2,
                    status="COLLISION" if dr.status == DuplicateStatus.DETECTED else to_str(dr.status),
                    metadata={
                        "match_type": to_str(dr.match_type),
                        "similarity_score": dr.similarity_score,
                        "explanation": dr.explanation,
                        "status": to_str(dr.status)
                    }
                )
                add_edge(doc_node, dup_node_id, "HAS_DUPLICATE_CANDIDATE", "ANOMALY", 1.0)

        # Officer Decisions
        decisions = self.db.query(WorkflowDecision).filter(
            WorkflowDecision.application_id == application_id
        ).all()
        for d in decisions:
            dec_node_id = f"decision_{d.id}"
            dec_val = to_str(d.decision)
            add_node(
                node_id=dec_node_id,
                label=f"Decision: {dec_val}",
                node_type="OFFICER_DECISION",
                tier=4,
                status=dec_val,
                metadata={
                    "officer_name": d.officer.full_name if d.officer else "Officer",
                    "decided_at": d.decided_at.strftime("%Y-%m-%d %H:%M") if d.decided_at else "N/A",
                    "justification": d.justification,
                    "is_override": d.is_override,
                    "override_reason": d.override_reason
                }
            )
            add_edge(dec_node_id, app_node_id, "RESOLVED_BY", "DECISION_FINAL", 1.0)

        # =========================================================================
        # CONTRADICTORY CLAIMS & DISCREPANCIES COMPUTATION
        # =========================================================================
        contradictory_claims = []

        # 1. Land Area Check
        try:
            if app.declared_land_acres is not None and inst.land_area_acres is not None:
                dec_land = float(app.declared_land_acres)
                base_land = float(inst.land_area_acres)
                diff = dec_land - base_land
                if abs(diff) > 0.01:
                    contradictory_claims.append({
                        "id": "DISC-LAND-01",
                        "category": "PHYSICAL_INFRASTRUCTURE",
                        "title": "Land Area Declaration vs Institution Baseline",
                        "severity": "CRITICAL" if diff < 0 else "WARNING",
                        "claim_label": "Application Declared Land",
                        "claim_value": f"{dec_land} Acres",
                        "evidence_label": "Institution Baseline Record",
                        "evidence_value": f"{base_land} Acres",
                        "discrepancy_delta": f"{round(diff, 2)} Acres difference",
                        "explanation": f"Declared land in Application ({dec_land} Acres) deviates from AICTE approved baseline land ({base_land} Acres).",
                        "suggested_action": "Verify Land Title Deed, Land Conversion Certificate, and Khasra records."
                    })
        except Exception:
            pass

        # 2. Intake Capacity Check
        try:
            if app.declared_intake is not None and inst.approved_intake is not None:
                dec_intake = int(app.declared_intake)
                base_intake = int(inst.approved_intake)
                intake_diff = dec_intake - base_intake
                if intake_diff > 0:
                    contradictory_claims.append({
                        "id": "DISC-INTAKE-01",
                        "category": "ACADEMIC_INTAKE",
                        "title": "Sanctioned Intake Expansion Shortfall",
                        "severity": "MAJOR",
                        "claim_label": "Application Requested Intake",
                        "claim_value": f"{dec_intake} Seats",
                        "evidence_label": "Previously Sanctioned Intake",
                        "evidence_value": f"{base_intake} Seats",
                        "discrepancy_delta": f"+{intake_diff} Seats undeclared increase",
                        "explanation": f"The application requests an intake of {dec_intake} seats exceeding previous sanctioned baseline by {intake_diff} seats without accredited faculty expansion proof.",
                        "suggested_action": "Submit approved faculty ratio proof and university NOC for intake expansion."
                    })
        except Exception:
            pass

        # 3. Check for expired certificates in extracted fields
        for claim in all_extracted_claims:
            key_lower = claim["field_key"].lower()
            val = str(claim["extracted_value"])
            if "valid" in key_lower or "date" in key_lower:
                if "2024" in val or "2025" in val or "expired" in val.lower():
                    contradictory_claims.append({
                        "id": f"DISC-EXP-{claim['field_id']}",
                        "category": "DOCUMENT_AUTHENTICITY",
                        "title": f"Expired Evidence: {claim['field_label']}",
                        "severity": "CRITICAL",
                        "claim_label": "Declared Valid Period",
                        "claim_value": f"Academic Year {app.academic_year}",
                        "evidence_label": f"Extracted from {claim['document_title']}",
                        "evidence_value": val,
                        "discrepancy_delta": "Certificate Validity Expired",
                        "explanation": f"Document '{claim['document_title']}' has validity '{val}' which does not cover the complete scrutiny academic cycle.",
                        "suggested_action": "Upload renewed certificate or valid extension order issued by competent authority."
                    })

        # =========================================================================
        # DUPLICATE DOCUMENT CANDIDATES (Cryptographic SHA-256 Collision Scan)
        # =========================================================================
        duplicate_candidates = []
        for doc in docs:
            v_latest = self.db.query(DocumentVersion).filter(
                DocumentVersion.document_id == doc.id
            ).order_by(DocumentVersion.version_number.desc()).first()

            if v_latest and v_latest.file_hash:
                other_versions = self.db.query(DocumentVersion).join(Document).join(Application).filter(
                    DocumentVersion.file_hash == v_latest.file_hash,
                    DocumentVersion.id != v_latest.id
                ).all()

                for ov in other_versions:
                    ov_app = ov.document.application
                    ov_inst = ov_app.institution
                    is_cross_institution = (ov_inst.id != inst.id)

                    duplicate_candidates.append({
                        "id": f"DUP-{doc.id}-{ov.id}",
                        "document_id": doc.id,
                        "document_title": doc.title,
                        "file_hash": v_latest.file_hash,
                        "matched_version_id": ov.id,
                        "matched_application_ref": ov_app.reference_no,
                        "matched_institution_name": ov_inst.name,
                        "is_cross_institution": is_cross_institution,
                        "similarity_score": 1.0,
                        "severity": "CRITICAL" if is_cross_institution else "INFO",
                        "description": f"Identical SHA-256 fingerprint matches document in Application {ov_app.reference_no} ({ov_inst.name})."
                    })

        # =========================================================================
        # RELATIONSHIP TABLE TRIPLETS
        # =========================================================================
        node_lookup = {n["id"]: n for n in nodes}
        relationship_table = []

        for e in edges:
            src = node_lookup.get(e["source"])
            tgt = node_lookup.get(e["target"])
            if src and tgt:
                relationship_table.append({
                    "source_id": e["source"],
                    "source_label": src["label"],
                    "source_type": src["type"],
                    "source_tier": src["tier"],
                    "relation": e["label"],
                    "target_id": e["target"],
                    "target_label": tgt["label"],
                    "target_type": tgt["type"],
                    "target_tier": tgt["tier"],
                    "edge_type": e["type"],
                    "confidence": e.get("confidence", 1.0)
                })

        return {
            "application_id": application_id,
            "reference_no": app.reference_no,
            "institution_name": inst.name,
            "nodes": nodes,
            "edges": edges,
            "finding_paths": finding_paths,
            "contradictory_claims": contradictory_claims,
            "duplicate_candidates": duplicate_candidates,
            "relationship_table": relationship_table,
            "extracted_claims": all_extracted_claims,
            "summary": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "tier_0_count": sum(1 for n in nodes if n["tier"] == 0),
                "tier_1_count": sum(1 for n in nodes if n["tier"] == 1),
                "tier_2_count": sum(1 for n in nodes if n["tier"] == 2),
                "tier_3_count": sum(1 for n in nodes if n["tier"] == 3),
                "tier_4_count": sum(1 for n in nodes if n["tier"] == 4),
                "findings_count": len(findings),
                "contradictions_count": len(contradictory_claims),
                "duplicates_count": len(duplicate_candidates)
            }
        }
