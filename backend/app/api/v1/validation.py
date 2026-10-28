from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.institution import InstitutionMembership
from app.models.application import Application, ApplicationStatus
from app.models.finding import ValidationFinding, ValidationRun, FindingStatus, TriggerType
from app.schemas.all_schemas import ValidationFindingResponse, ValidationRunResponse
from app.services.rules_engine import ComplianceRulesEngine
from app.services.anomaly_detector import AnomalyDetector
from app.services.audit_service import record_audit_event

router = APIRouter(tags=["Regulatory Validation"])


@router.post("/applications/{application_id}/validate", response_model=ValidationRunResponse)
def run_validation(
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

    engine = ComplianceRulesEngine(db)
    val_run = engine.execute_validation_run(
        application_id=application_id,
        trigger_type=TriggerType.MANUAL_TRIGGER,
        triggering_change=f"Scrutiny validation triggered by {current_user.full_name}"
    )

    # Transition application status to UNDER_REVIEW if currently SUBMITTED
    if app.status == ApplicationStatus.SUBMITTED:
        app.status = ApplicationStatus.UNDER_REVIEW
        db.commit()

    record_audit_event(
        db=db,
        action="RUN_VALIDATION_RULES",
        entity_type="APPLICATION",
        entity_id=str(app.id),
        actor=current_user,
        details=f"Validation Run #{val_run.run_number} finished. Rules evaluated: {val_run.total_rules_evaluated}, Passed: {val_run.passed_count}, Failed: {val_run.failed_count}."
    )

    return get_validation_run_detail(val_run.id, current_user, db)


@router.get("/applications/{application_id}/findings", response_model=List[ValidationFindingResponse])
def list_application_findings(
    application_id: int,
    include_historic: bool = Query(False, description="Include superseded findings from earlier runs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    query = db.query(ValidationFinding).filter(ValidationFinding.application_id == application_id)
    if not include_historic:
        query = query.filter(ValidationFinding.is_active == True)

    findings = query.order_by(ValidationFinding.id.asc()).all()
    results = []
    for f in findings:
        doc_title = None
        if f.affected_document_version:
            doc_title = f.affected_document_version.document.title

        results.append({
            "id": f.id,
            "rule_code": f.rule.rule_code,
            "rule_title": f.rule.title,
            "category": f.rule.category.value,
            "status": f.status.value,
            "severity": f.severity,
            "affected_claim_field": f.affected_claim_field,
            "affected_document_version_id": f.affected_document_version_id,
            "document_title": doc_title,
            "expected_value": f.expected_value,
            "observed_value": f.observed_value,
            "explanation": f.explanation,
            "recommended_action": f.recommended_action,
            "source_page": f.source_page,
            "is_active": f.is_active,
            "is_resolved": f.is_resolved,
            "created_at": f.created_at
        })
    return results


@router.get("/applications/{application_id}/anomalies")
def detect_application_anomalies(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes explainable anomaly and duplicate screening (Stage 7).
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    detector = AnomalyDetector(db)
    anomalies = detector.scan_application_anomalies(application_id)
    return {
        "application_id": application_id,
        "reference_no": app.reference_no,
        "total_anomalies": len(anomalies),
        "anomalies": anomalies
    }


@router.get("/validation-runs/{run_id}", response_model=ValidationRunResponse)
def get_validation_run_detail(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    val_run = db.query(ValidationRun).filter(ValidationRun.id == run_id).first()
    if not val_run:
        raise HTTPException(status_code=404, detail="Validation run not found")

    findings = db.query(ValidationFinding).filter(
        ValidationFinding.validation_run_id == val_run.id
    ).all()

    findings_resp = []
    for f in findings:
        doc_title = None
        if f.affected_document_version:
            doc_title = f.affected_document_version.document.title

        findings_resp.append({
            "id": f.id,
            "rule_code": f.rule.rule_code,
            "rule_title": f.rule.title,
            "category": f.rule.category.value,
            "status": f.status.value,
            "severity": f.severity,
            "affected_claim_field": f.affected_claim_field,
            "affected_document_version_id": f.affected_document_version_id,
            "document_title": doc_title,
            "expected_value": f.expected_value,
            "observed_value": f.observed_value,
            "explanation": f.explanation,
            "recommended_action": f.recommended_action,
            "source_page": f.source_page,
            "is_active": f.is_active,
            "is_resolved": f.is_resolved,
            "created_at": f.created_at
        })

    return {
        "id": val_run.id,
        "run_number": val_run.run_number,
        "trigger_type": val_run.trigger_type.value,
        "triggering_change": val_run.triggering_change,
        "total_rules_evaluated": val_run.total_rules_evaluated,
        "passed_count": val_run.passed_count,
        "failed_count": val_run.failed_count,
        "warning_count": val_run.warning_count,
        "manual_review_count": val_run.manual_review_count,
        "reused_checks_count": val_run.reused_checks_count,
        "executed_at": val_run.executed_at,
        "findings": findings_resp
    }

