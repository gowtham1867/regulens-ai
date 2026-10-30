import io
import csv
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.application import Application, ApplicationStatus
from app.models.institution import Institution
from app.models.user import User, UserRole
from app.models.workflow_routing import ApplicationWorkflowRouting, StageMovementHistory
from app.models.obligation import Obligation, ObligationStatus, ClockState
from app.models.evc import EVCSchedule, EVCStatus
from app.models.undertaking import TimeBoundUndertaking, UndertakingStatus
from app.models.document_validity import DocumentValidityRecord, DocumentValidityStatus
from app.models.audit import AuditEvent
from app.services.audit_service import verify_audit_chain_integrity


def sanitize_csv(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


class ComplianceReportsService:
    @classmethod
    def get_report_data(cls, db: Session, report_key: str) -> Dict[str, Any]:
        """
        Dispatches and generates data for one of the 11 official regulatory compliance reports.
        """
        handlers = {
            "pendency_ageing": cls.report_pendency_ageing,
            "route_distribution": cls.report_route_distribution,
            "stage_bottlenecks": cls.report_stage_bottlenecks,
            "regional_pendency": cls.report_regional_pendency,
            "officer_workload": cls.report_officer_workload,
            "obligations_status": cls.report_obligations_status,
            "evc_tracking": cls.report_evc_tracking,
            "undertakings_compliance": cls.report_undertakings_compliance,
            "document_validity": cls.report_document_validity,
            "escalation_breaches": cls.report_escalation_breaches,
            "audit_chain_integrity": cls.report_audit_chain_integrity,
        }
        handler = handlers.get(report_key)
        if not handler:
            raise ValueError(f"Unknown report key: {report_key}")
        return handler(db)

    @classmethod
    def generate_csv_for_report(cls, db: Session, report_key: str) -> str:
        data = cls.get_report_data(db, report_key)
        rows = data.get("rows", [])
        headers = data.get("headers", [])

        output = io.StringIO()
        output.write("\ufeff")  # UTF-8 BOM
        writer = csv.DictWriter(output, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for r in rows:
            sanitized = {k: sanitize_csv(r.get(k, "")) for k in headers}
            writer.writerow(sanitized)
        return output.getvalue()

    # -------------------------------------------------------------------------
    # 1. Application Pendency & Ageing Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_pendency_ageing(cls, db: Session) -> Dict[str, Any]:
        now = datetime.utcnow()
        apps = db.query(Application).filter(
            Application.status.notin_([ApplicationStatus.APPROVED, ApplicationStatus.REJECTED])
        ).all()

        bands = {"under_15": 0, "15_to_30": 0, "30_to_60": 0, "over_60": 0}
        rows = []
        total_age = 0

        for a in apps:
            created = a.submission_date or a.created_at or now
            age_days = max(0, (now - created).days)
            total_age += age_days

            if age_days < 15:
                bands["under_15"] += 1
                band_label = "< 15 Days"
            elif age_days <= 30:
                bands["15_to_30"] += 1
                band_label = "15-30 Days"
            elif age_days <= 60:
                bands["30_to_60"] += 1
                band_label = "30-60 Days"
            else:
                bands["over_60"] += 1
                band_label = "> 60 Days (Critical Pendency)"

            rows.append({
                "reference_no": a.reference_no,
                "institution_name": a.institution.name if a.institution else "N/A",
                "category": a.category.value if hasattr(a.category, "value") else str(a.category),
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "age_days": age_days,
                "ageing_band": band_label,
                "submission_date": created.strftime("%Y-%m-%d")
            })

        avg_days = round(total_age / len(apps), 1) if apps else 0.0

        return {
            "title": "Application Pendency & Ageing Report",
            "headers": ["reference_no", "institution_name", "category", "status", "age_days", "ageing_band", "submission_date"],
            "summary": {
                "total_pending": len(apps),
                "average_age_days": avg_days,
                "bands": bands
            },
            "rows": rows
        }

    # -------------------------------------------------------------------------
    # 2. Workflow Route Distribution Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_route_distribution(cls, db: Session) -> Dict[str, Any]:
        routings = db.query(ApplicationWorkflowRouting).all()
        distribution: Dict[str, int] = {}
        rows = []

        for r in routings:
            rtype = r.route_type
            distribution[rtype] = distribution.get(rtype, 0) + 1
            app = r.application
            rows.append({
                "application_reference": app.reference_no if app else f"App #{r.application_id}",
                "institution_name": app.institution.name if app and app.institution else "N/A",
                "route_type": r.route_type,
                "current_stage": r.current_stage,
                "processing_status": r.processing_status,
                "routing_reason": r.routing_reason
            })

        return {
            "title": "Workflow Route Distribution Report",
            "headers": ["application_reference", "institution_name", "route_type", "current_stage", "processing_status", "routing_reason"],
            "summary": {
                "total_routed_applications": len(routings),
                "route_counts": distribution
            },
            "rows": rows
        }

    # -------------------------------------------------------------------------
    # 3. Stage-wise Bottleneck Analysis Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_stage_bottlenecks(cls, db: Session) -> Dict[str, Any]:
        routings = db.query(ApplicationWorkflowRouting).all()
        stage_counts: Dict[str, int] = {}
        rows = []
        now = datetime.utcnow()

        for r in routings:
            stage_counts[r.current_stage] = stage_counts.get(r.current_stage, 0) + 1
            entry = r.stage_entry_at or now
            days_in_stage = max(0, (now - entry).days)
            app = r.application

            rows.append({
                "application_reference": app.reference_no if app else f"App #{r.application_id}",
                "stage": r.current_stage,
                "route_type": r.route_type,
                "days_in_current_stage": days_in_stage,
                "stage_deadline": r.stage_deadline.strftime("%Y-%m-%d") if r.stage_deadline else "N/A",
                "is_delayed": days_in_stage > 15
            })

        return {
            "title": "Stage-wise Bottleneck Analysis Report",
            "headers": ["application_reference", "stage", "route_type", "days_in_current_stage", "stage_deadline", "is_delayed"],
            "summary": {
                "total_tracked": len(routings),
                "stage_distribution": stage_counts
            },
            "rows": rows
        }

    # -------------------------------------------------------------------------
    # 4. Regional Pendency & Workload Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_regional_pendency(cls, db: Session) -> Dict[str, Any]:
        insts = db.query(Institution).all()
        regional_stats: Dict[str, Dict[str, int]] = {}
        rows = []

        for inst in insts:
            region = f"{inst.state} Regional Directorate"
            if region not in regional_stats:
                regional_stats[region] = {"institutions": 0, "applications": 0, "pending": 0}
            
            regional_stats[region]["institutions"] += 1
            for app in inst.applications:
                regional_stats[region]["applications"] += 1
                if app.status not in [ApplicationStatus.APPROVED, ApplicationStatus.REJECTED]:
                    regional_stats[region]["pending"] += 1

                rows.append({
                    "region": region,
                    "institution_name": inst.name,
                    "aicte_id": inst.aicte_id,
                    "application_reference": app.reference_no,
                    "status": app.status.value if hasattr(app.status, "value") else str(app.status)
                })

        return {
            "title": "Regional Pendency & Workload Report",
            "headers": ["region", "institution_name", "aicte_id", "application_reference", "status"],
            "summary": regional_stats,
            "rows": rows
        }

    # -------------------------------------------------------------------------
    # 5. Officer-wise Workload & Performance Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_officer_workload(cls, db: Session) -> Dict[str, Any]:
        officers = db.query(User).filter(User.role == UserRole.AICTE_OFFICER).all()
        rows = []
        summary = {}

        for off in officers:
            assigned_apps = db.query(Application).filter(Application.assigned_officer_id == off.id).count()
            rows.append({
                "officer_name": off.full_name or off.email,
                "officer_email": off.email,
                "assigned_applications": assigned_apps,
                "role": off.role.value if hasattr(off.role, "value") else str(off.role)
            })
            summary[off.email] = assigned_apps

        return {
            "title": "Officer-wise Workload & Performance Report",
            "headers": ["officer_name", "officer_email", "assigned_applications", "role"],
            "summary": summary,
            "rows": rows
        }

    # -------------------------------------------------------------------------
    # 6. Promise Ledger / Obligation Status Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_obligations_status(cls, db: Session) -> Dict[str, Any]:
        obls = db.query(Obligation).all()
        status_counts = {}
        rows = []

        for obl in obls:
            status_counts[obl.status] = status_counts.get(obl.status, 0) + 1
            rows.append({
                "obligation_no": obl.obligation_no,
                "title": obl.title,
                "type": obl.obligation_type,
                "responsible_entity": obl.responsible_entity,
                "responsible_role": obl.responsible_role,
                "status": obl.status,
                "clock_state": obl.clock_state,
                "aph_clause": obl.aph_clause,
                "due_date": obl.due_date.strftime("%Y-%m-%d"),
                "total_paused_days": obl.total_paused_days,
                "approved_extensions": obl.approved_extension_days
            })

        return {
            "title": "Promise Ledger / Obligation Status Report",
            "headers": ["obligation_no", "title", "type", "responsible_entity", "responsible_role", "status", "clock_state", "aph_clause", "due_date", "total_paused_days", "approved_extensions"],
            "summary": status_counts,
            "rows": rows
        }

    # -------------------------------------------------------------------------
    # 7. EVC Inspection Tracking Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_evc_tracking(cls, db: Session) -> Dict[str, Any]:
        evcs = db.query(EVCSchedule).all()
        status_counts = {}
        rows = []

        for evc in evcs:
            status_counts[evc.status] = status_counts.get(evc.status, 0) + 1
            rows.append({
                "evc_no": evc.evc_no,
                "institution_name": evc.institution.name if evc.institution else "N/A",
                "region": evc.region,
                "status": evc.status,
                "scheduled_date": evc.scheduled_date.strftime("%Y-%m-%d") if evc.scheduled_date else "UNSCHEDULED",
                "conflict_check_passed": evc.conflict_check_passed,
                "recommendation": evc.report_recommendation or "PENDING"
            })

        return {
            "title": "EVC Inspection Tracking Report",
            "headers": ["evc_no", "institution_name", "region", "status", "scheduled_date", "conflict_check_passed", "recommendation"],
            "summary": status_counts,
            "rows": rows
        }

    # -------------------------------------------------------------------------
    # 8. Time-Bound Undertaking Compliance Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_undertakings_compliance(cls, db: Session) -> Dict[str, Any]:
        uts = db.query(TimeBoundUndertaking).all()
        status_counts = {}
        rows = []

        for ut in uts:
            status_counts[ut.status] = status_counts.get(ut.status, 0) + 1
            rows.append({
                "undertaking_no": ut.undertaking_no,
                "institution_name": ut.institution.name if ut.institution else "N/A",
                "condition_title": ut.condition_title,
                "due_date": ut.due_date.strftime("%Y-%m-%d"),
                "status": ut.status,
                "evidence_submitted": "YES" if ut.evidence_submission_date else "NO",
                "aph_clause": ut.aph_clause
            })

        return {
            "title": "Time-Bound Undertaking Compliance Report",
            "headers": ["undertaking_no", "institution_name", "condition_title", "due_date", "status", "evidence_submitted", "aph_clause"],
            "summary": status_counts,
            "rows": rows
        }

    # -------------------------------------------------------------------------
    # 9. Document Expiry & Lease Monitoring Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_document_validity(cls, db: Session) -> Dict[str, Any]:
        docs = db.query(DocumentValidityRecord).all()
        status_counts = {}
        rows = []

        for d in docs:
            status_counts[d.status] = status_counts.get(d.status, 0) + 1
            rows.append({
                "institution_name": d.institution.name if d.institution else "N/A",
                "document_type": d.document_type,
                "document_name": d.document_name,
                "issuing_authority": d.issuing_authority,
                "expiry_date": d.expiry_date.strftime("%Y-%m-%d"),
                "days_remaining": d.days_remaining,
                "status": d.status
            })

        return {
            "title": "Document Expiry & Lease Monitoring Report",
            "headers": ["institution_name", "document_type", "document_name", "issuing_authority", "expiry_date", "days_remaining", "status"],
            "summary": status_counts,
            "rows": rows
        }

    # -------------------------------------------------------------------------
    # 10. Alert Escalation & Statutory Breach Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_escalation_breaches(cls, db: Session) -> Dict[str, Any]:
        escalated_obls = db.query(Obligation).filter(Obligation.escalation_level > 0).all()
        rows = []

        for obl in escalated_obls:
            rows.append({
                "obligation_no": obl.obligation_no,
                "institution_name": obl.institution.name if obl.institution else "N/A",
                "title": obl.title,
                "responsible_entity": obl.responsible_entity,
                "escalation_level": obl.escalation_level,
                "due_date": obl.due_date.strftime("%Y-%m-%d"),
                "status": obl.status,
                "clock_state": obl.clock_state,
                "aph_clause": obl.aph_clause
            })

        return {
            "title": "Alert Escalation & Statutory Breach Report",
            "headers": ["obligation_no", "institution_name", "title", "responsible_entity", "escalation_level", "due_date", "status", "clock_state", "aph_clause"],
            "summary": {
                "total_escalations": len(escalated_obls),
                "level_1_reminders": sum(1 for o in escalated_obls if o.escalation_level == 1),
                "level_2_warnings": sum(1 for o in escalated_obls if o.escalation_level == 2),
                "level_3_breaches": sum(1 for o in escalated_obls if o.escalation_level >= 3)
            },
            "rows": rows
        }

    # -------------------------------------------------------------------------
    # 11. Cryptographic Audit Chain Verification Report
    # -------------------------------------------------------------------------
    @classmethod
    def report_audit_chain_integrity(cls, db: Session) -> Dict[str, Any]:
        result = verify_audit_chain_integrity(db)
        events = db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(50).all()
        rows = []

        for ev in events:
            rows.append({
                "event_id": ev.id,
                "timestamp": ev.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "actor_email": ev.actor_email,
                "action": ev.action,
                "entity_type": ev.entity_type,
                "entity_id": ev.entity_id,
                "entry_hash": ev.entry_hash[:16] + "...",
                "previous_hash": (ev.previous_hash[:16] + "...") if ev.previous_hash else "GENESIS"
            })

        return {
            "title": "Cryptographic Audit Chain Verification Report",
            "headers": ["event_id", "timestamp", "actor_email", "action", "entity_type", "entity_id", "entry_hash", "previous_hash"],
            "summary": {
                "integrity_status": result["status"],
                "is_valid": result["valid"],
                "total_events": result["total_events"],
                "latest_hash": result.get("latest_hash", "N/A"),
                "verified_at": result.get("verified_at", datetime.utcnow().isoformat())
            },
            "rows": rows
        }
