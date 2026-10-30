from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import io
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.institution import Institution, InstitutionMembership
from app.models.application import Application
from app.services.report_generator import ReportGenerator
from app.services.audit_service import record_audit_event

router = APIRouter(tags=["Reports & Exports"])


@router.get("/applications/export.csv")
def export_applications_queue_csv(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export the full application queue (or filtered set) as a clean, standardized CSV.
    Enforces strict role-based institution isolation and UTF-8 BOM encoding.
    """
    query = db.query(Application)

    # Role-based institution isolation
    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership:
            return Response(content="\ufeff", media_type="text/csv; charset=utf-8")
        query = query.filter(Application.institution_id == membership.institution_id)

    if status_filter:
        query = query.filter(Application.status == status_filter)
    if category_filter:
        query = query.filter(Application.category == category_filter)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.join(Institution).filter(
            (Application.reference_no.ilike(search_fmt)) |
            (Application.title.ilike(search_fmt)) |
            (Institution.name.ilike(search_fmt)) |
            (Institution.aicte_id.ilike(search_fmt))
        )

    apps = query.order_by(desc(Application.updated_at)).all()
    generator = ReportGenerator(db)
    csv_text = generator.generate_applications_queue_csv(apps)

    record_audit_event(
        db=db,
        action="EXPORT_APPLICATIONS_CSV",
        entity_type="APPLICATION_QUEUE",
        entity_id="ALL",
        actor=current_user,
        details=f"Exported {len(apps)} applications to CSV (status={status_filter or 'ALL'}, category={category_filter or 'ALL'}, search={search or 'NONE'})"
    )

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="regulens_applications_{today_str}.csv"'}
    )


@router.get("/applications/{application_id}/report.csv")
def export_application_csv(
    application_id: int,
    export_type: str = Query("findings", description="Export type: 'findings' or 'documents'"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership or membership.institution_id != app.institution_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

    generator = ReportGenerator(db)
    csv_text = generator.generate_csv_report(application_id, export_type=export_type)

    record_audit_event(
        db=db,
        action="EXPORT_REPORT_CSV",
        entity_type="APPLICATION",
        entity_id=str(application_id),
        actor=current_user,
        details=f"CSV compliance report ({export_type}) exported for {app.reference_no}"
    )

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    clean_ref = app.reference_no.replace(" ", "_").replace("/", "-")
    filename = f"regulens_{export_type}_{clean_ref}_{today_str}.csv"

    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/applications/{application_id}/report.pdf")
def export_application_pdf(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership or membership.institution_id != app.institution_id:
            raise HTTPException(status_code=403, detail="Unauthorized")

    generator = ReportGenerator(db)
    pdf_bytes = generator.generate_pdf_report(application_id)

    record_audit_event(
        db=db,
        action="EXPORT_REPORT_PDF",
        entity_type="APPLICATION",
        entity_id=str(application_id),
        actor=current_user,
        details=f"PDF compliance scrutiny report generated for {app.reference_no}"
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=ReguLens_Scrutiny_{app.reference_no}.pdf"}
    )


# =============================================================================
# SIH 26262: 11 SPECIALIZED COMPLIANCE & PENDENCY REPORTS
# =============================================================================

@router.get("/compliance-reports")
def list_compliance_reports():
    return [
        {"key": "pendency_ageing", "title": "Application Pendency & Ageing Report", "category": "Workload"},
        {"key": "route_distribution", "title": "Workflow Route Distribution Report", "category": "Routing"},
        {"key": "stage_bottlenecks", "title": "Stage-wise Bottleneck Analysis Report", "category": "Performance"},
        {"key": "regional_pendency", "title": "Regional Pendency & Workload Report", "category": "Regional"},
        {"key": "officer_workload", "title": "Officer-wise Workload & Performance Report", "category": "Performance"},
        {"key": "obligations_status", "title": "Promise Ledger / Obligation Status Report", "category": "Obligations"},
        {"key": "evc_tracking", "title": "EVC Inspection Tracking Report", "category": "Inspection"},
        {"key": "undertakings_compliance", "title": "Time-Bound Undertaking Compliance Report", "category": "Undertakings"},
        {"key": "document_validity", "title": "Document Expiry & Lease Monitoring Report", "category": "Documents"},
        {"key": "escalation_breaches", "title": "Alert Escalation & Statutory Breach Report", "category": "Escalations"},
        {"key": "audit_chain_integrity", "title": "Cryptographic Audit Chain Verification Report", "category": "Security & Audit"},
    ]


@router.get("/compliance-reports/{report_key}")
def get_compliance_report(
    report_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        from app.services.compliance_reports_service import ComplianceReportsService
        data = ComplianceReportsService.get_report_data(db, report_key)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/compliance-reports/{report_key}/export.csv")
def export_compliance_report_csv(
    report_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        from app.services.compliance_reports_service import ComplianceReportsService
        csv_text = ComplianceReportsService.generate_csv_for_report(db, report_key)
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        return Response(
            content=csv_text,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="regulens_{report_key}_{today_str}.csv"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


