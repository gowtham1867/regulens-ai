from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from app.database import get_db
from app.core.deps import get_current_user, get_current_institution_id
from app.models.user import User, UserRole
from app.models.institution import Institution, InstitutionMembership
from app.models.application import (
    Application,
    ApplicationCategory,
    ApplicationStatus,
    ApplicationClaim,
    ApplicationStatusHistory
)
from app.models.finding import ValidationFinding, FindingStatus
from app.models.document import Document
from app.schemas.all_schemas import ApplicationCreate, ApplicationResponse
from app.services.audit_service import record_audit_event
from app.services.notification_service import notify_all_officers
from app.services.report_generator import ReportGenerator

router = APIRouter(tags=["Applications"])


@router.get("/applications", response_model=List[ApplicationResponse])
def list_applications(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Application)

    # Role-based institution isolation
    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership:
            return []
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
    results = []
    for app in apps:
        # Calculate active findings
        findings = db.query(ValidationFinding).filter(
            ValidationFinding.application_id == app.id,
            ValidationFinding.is_active == True
        ).all()
        
        highest_sev = None
        if any(f.severity == "CRITICAL" and f.status != FindingStatus.PASSED for f in findings):
            highest_sev = "CRITICAL"
        elif any(f.severity == "MAJOR" and f.status != FindingStatus.PASSED for f in findings):
            highest_sev = "MAJOR"
        elif any(f.severity == "MINOR" and f.status != FindingStatus.PASSED for f in findings):
            highest_sev = "MINOR"

        results.append({
            "id": app.id,
            "reference_no": app.reference_no,
            "institution_id": app.institution_id,
            "institution_name": app.institution.name if app.institution else None,
            "title": app.title,
            "category": app.category.value,
            "academic_year": app.academic_year,
            "status": app.status.value,
            "declared_intake": app.declared_intake,
            "declared_land_acres": app.declared_land_acres,
            "declared_built_up_sqm": app.declared_built_up_sqm,
            "is_demo_seed": app.is_demo_seed,
            "submission_date": app.submission_date,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
            "assigned_officer_name": app.assigned_officer.full_name if app.assigned_officer else None,
            "findings_count": len(findings),
            "highest_severity": highest_sev
        })
    return results


@router.post("/applications", response_model=ApplicationResponse)
def create_application(
    app_in: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.INSTITUTION_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only registered institution users can initiate new applications"
        )

    membership = db.query(InstitutionMembership).filter(
        InstitutionMembership.user_id == current_user.id
    ).first()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No institution profile linked to current user"
        )

    # Generate unique application reference
    count = db.query(Application).count() + 1
    ref_no = f"AICTE-2025-APP-{count:04d}"

    new_app = Application(
        reference_no=ref_no,
        institution_id=membership.institution_id,
        submitting_user_id=current_user.id,
        title=app_in.title,
        category=app_in.category,
        academic_year=app_in.academic_year,
        status=ApplicationStatus.DRAFT,
        declared_intake=app_in.declared_intake,
        declared_land_acres=app_in.declared_land_acres,
        declared_built_up_sqm=app_in.declared_built_up_sqm,
        notes=app_in.notes,
        is_demo_seed=False,
        created_at=datetime.utcnow()
    )
    db.add(new_app)
    db.flush()

    # Pre-populate required document placeholders for extension of approval
    doc_types = [
        ("LAND_DOCUMENT", "Land Ownership / Lease Deed Document"),
        ("FIRE_SAFETY_CERTIFICATE", "Fire Safety Certificate / NOC"),
        ("AFFILIATION_CERTIFICATE", "University Affiliation Letter"),
        ("BUILDING_PLAN", "Approved Architectural Building Plan")
    ]
    for dt, title in doc_types:
        d = Document(
            application_id=new_app.id,
            document_type=dt,
            title=title,
            is_required=True
        )
        db.add(d)

    # Status history
    hist = ApplicationStatusHistory(
        application_id=new_app.id,
        to_status=ApplicationStatus.DRAFT.value,
        changed_by_user_id=current_user.id,
        reason="Application draft created"
    )
    db.add(hist)
    db.commit()
    db.refresh(new_app)

    record_audit_event(
        db=db,
        action="CREATE_APPLICATION_DRAFT",
        entity_type="APPLICATION",
        entity_id=str(new_app.id),
        actor=current_user,
        details=f"Draft application {ref_no} initiated for {membership.institution.name}"
    )

    return {
        "id": new_app.id,
        "reference_no": new_app.reference_no,
        "institution_id": new_app.institution_id,
        "institution_name": membership.institution.name,
        "title": new_app.title,
        "category": new_app.category.value,
        "academic_year": new_app.academic_year,
        "status": new_app.status.value,
        "declared_intake": new_app.declared_intake,
        "declared_land_acres": new_app.declared_land_acres,
        "declared_built_up_sqm": new_app.declared_built_up_sqm,
        "is_demo_seed": new_app.is_demo_seed,
        "submission_date": new_app.submission_date,
        "created_at": new_app.created_at,
        "updated_at": new_app.updated_at,
        "assigned_officer_name": None,
        "findings_count": 0,
        "highest_severity": None
    }


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


@router.get("/applications/{application_id}", response_model=ApplicationResponse)
def get_application_detail(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Isolation check
    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership or membership.institution_id != app.institution_id:
            raise HTTPException(status_code=403, detail="Unauthorized to access this institutional application")

    findings = db.query(ValidationFinding).filter(
        ValidationFinding.application_id == app.id,
        ValidationFinding.is_active == True
    ).all()
    
    highest_sev = None
    if any(f.severity == "CRITICAL" and f.status != FindingStatus.PASSED for f in findings):
        highest_sev = "CRITICAL"
    elif any(f.severity == "MAJOR" and f.status != FindingStatus.PASSED for f in findings):
        highest_sev = "MAJOR"
    elif any(f.severity == "MINOR" and f.status != FindingStatus.PASSED for f in findings):
        highest_sev = "MINOR"

    return {
        "id": app.id,
        "reference_no": app.reference_no,
        "institution_id": app.institution_id,
        "institution_name": app.institution.name,
        "title": app.title,
        "category": app.category.value,
        "academic_year": app.academic_year,
        "status": app.status.value,
        "declared_intake": app.declared_intake,
        "declared_land_acres": app.declared_land_acres,
        "declared_built_up_sqm": app.declared_built_up_sqm,
        "is_demo_seed": app.is_demo_seed,
        "submission_date": app.submission_date,
        "created_at": app.created_at,
        "updated_at": app.updated_at,
        "assigned_officer_name": app.assigned_officer.full_name if app.assigned_officer else None,
        "findings_count": len(findings),
        "highest_severity": highest_sev
    }


@router.post("/applications/{application_id}/submit", response_model=ApplicationResponse)
def submit_application(
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

    if app.status != ApplicationStatus.DRAFT:
        raise HTTPException(status_code=400, detail=f"Cannot submit application in status '{app.status.value}'")

    old_status = app.status.value
    app.status = ApplicationStatus.SUBMITTED
    app.submission_date = datetime.utcnow()

    # Assign to an officer if available
    officer = db.query(User).filter(User.role == UserRole.AICTE_OFFICER, User.is_active == True).first()
    if officer:
        app.assigned_officer_id = officer.id

    # Record status transition
    hist = ApplicationStatusHistory(
        application_id=app.id,
        from_status=old_status,
        to_status=ApplicationStatus.SUBMITTED.value,
        changed_by_user_id=current_user.id,
        reason="Formal institutional submission"
    )
    db.add(hist)
    db.commit()

    record_audit_event(
        db=db,
        action="SUBMIT_APPLICATION",
        entity_type="APPLICATION",
        entity_id=str(app.id),
        actor=current_user,
        before_state={"status": old_status},
        after_state={"status": app.status.value},
        details=f"Application {app.reference_no} officially submitted for regulatory review."
    )

    notify_all_officers(
        db=db,
        title="New Application Submitted",
        message=f"{app.institution.name} submitted application {app.reference_no} for scrutiny.",
        notification_type="INFO",
        link=f"/officer/applications/{app.id}"
    )

    return get_application_detail(app.id, current_user, db)


@router.get("/dashboard/summary")
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns real operational dashboard counts calculated strictly from database records (Rule 2).
    """
    app_query = db.query(Application)
    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if membership:
            app_query = app_query.filter(Application.institution_id == membership.institution_id)
        else:
            return {"total_applications": 0}

    total_apps = app_query.count()
    draft_apps = app_query.filter(Application.status == ApplicationStatus.DRAFT).count()
    submitted_apps = app_query.filter(Application.status == ApplicationStatus.SUBMITTED).count()
    under_review = app_query.filter(Application.status == ApplicationStatus.UNDER_REVIEW).count()
    awaiting_clarification = app_query.filter(Application.status == ApplicationStatus.CLARIFICATION_REQUESTED).count()
    correction_submitted = app_query.filter(Application.status == ApplicationStatus.CORRECTION_SUBMITTED).count()
    ready_for_decision = app_query.filter(Application.status == ApplicationStatus.READY_FOR_DECISION).count()
    approved_apps = app_query.filter(Application.status == ApplicationStatus.APPROVED).count()
    returned_apps = app_query.filter(Application.status == ApplicationStatus.RETURNED).count()
    rejected_apps = app_query.filter(Application.status == ApplicationStatus.REJECTED).count()

    # Active findings count
    findings_query = db.query(ValidationFinding).filter(ValidationFinding.is_active == True)
    if current_user.role == UserRole.INSTITUTION_USER and membership:
        findings_query = findings_query.join(Application).filter(Application.institution_id == membership.institution_id)

    total_findings = findings_query.count()
    critical_deficiencies = findings_query.filter(
        ValidationFinding.status == FindingStatus.FAILED,
        ValidationFinding.severity == "CRITICAL"
    ).count()
    active_warnings = findings_query.filter(ValidationFinding.status == FindingStatus.WARNING).count()
    manual_reviews_pending = findings_query.filter(ValidationFinding.status == FindingStatus.MANUAL_REVIEW_REQUIRED).count()

    return {
        "total_applications": total_apps,
        "draft_applications": draft_apps,
        "submitted_applications": submitted_apps,
        "under_review_applications": under_review,
        "awaiting_clarification": awaiting_clarification,
        "correction_submitted": correction_submitted,
        "ready_for_decision": ready_for_decision,
        "approved_applications": approved_apps,
        "returned_applications": returned_apps,
        "rejected_applications": rejected_apps,
        "active_findings": total_findings,
        "critical_deficiencies": critical_deficiencies,
        "active_warnings": active_warnings,
        "manual_reviews_pending": manual_reviews_pending,
        "evaluated_at": datetime.utcnow().isoformat()
    }

