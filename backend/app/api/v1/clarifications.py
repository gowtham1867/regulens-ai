import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.institution import InstitutionMembership
from app.models.application import Application, ApplicationStatus, ApplicationStatusHistory
from app.models.document import Document, DocumentVersion
from app.models.workflow import ClarificationRequest, ClarificationStatus, CorrectionSubmission
from app.schemas.all_schemas import (
    ClarificationRequestCreate,
    ClarificationResponse,
    ValidationRunResponse
)
from app.services.revalidation_service import RevalidationService
from app.services.ocr_engine import OCREngine
from app.services.audit_service import record_audit_event
from app.services.notification_service import create_notification, notify_institution_users

router = APIRouter(tags=["Clarifications & Corrections"])


@router.post("/applications/{application_id}/clarifications", response_model=ClarificationResponse)
def create_clarification_request(
    application_id: int,
    req_in: ClarificationRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Only AICTE Officers can initiate clarification requests")

    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    due_dt = datetime.utcnow() + timedelta(days=req_in.due_days or 7)

    clarification = ClarificationRequest(
        application_id=application_id,
        requesting_officer_id=current_user.id,
        subject=req_in.subject,
        requested_information=req_in.requested_information,
        instructions_for_correction=req_in.instructions_for_correction,
        relevant_finding_id=req_in.relevant_finding_id,
        relevant_document_id=req_in.relevant_document_id,
        status=ClarificationStatus.OPEN,
        due_date=due_dt,
        created_at=datetime.utcnow()
    )
    db.add(clarification)

    # Transition application status to CLARIFICATION_REQUESTED
    old_status = app.status.value
    app.status = ApplicationStatus.CLARIFICATION_REQUESTED

    status_history = ApplicationStatusHistory(
        application_id=app.id,
        from_status=old_status,
        to_status=app.status.value,
        changed_by_user_id=current_user.id,
        reason=f"Clarification requested: {req_in.subject}",
        created_at=datetime.utcnow()
    )
    db.add(status_history)
    db.commit()
    db.refresh(clarification)

    record_audit_event(
        db=db,
        action="REQUEST_CLARIFICATION",
        entity_type="CLARIFICATION_REQUEST",
        entity_id=str(clarification.id),
        actor=current_user,
        before_state={"status": old_status},
        after_state={"status": app.status.value},
        details=f"Clarification requested for Application {app.reference_no}: '{req_in.subject}'"
    )

    # Strictly notify affiliated institution users
    notify_institution_users(
        db=db,
        institution_id=app.institution_id,
        title="Clarification Requested by AICTE Scrutiny Officer",
        message=f"Clarification requested for Application {app.reference_no}: {req_in.subject}. Due: {due_dt.strftime('%d-%b-%Y')}",
        notification_type="WARNING",
        link=f"/applications/{app.id}",
        application_id=app.id,
        action_type="CLARIFICATION_REQUESTED",
        details=req_in.instructions_for_correction or req_in.requested_information
    )

    doc_title = clarification.relevant_document.title if clarification.relevant_document else None

    return {
        "id": clarification.id,
        "application_id": clarification.application_id,
        "application_ref": app.reference_no,
        "officer_name": current_user.full_name,
        "subject": clarification.subject,
        "requested_information": clarification.requested_information,
        "instructions_for_correction": clarification.instructions_for_correction,
        "relevant_finding_id": clarification.relevant_finding_id,
        "relevant_document_id": clarification.relevant_document_id,
        "relevant_document_title": doc_title,
        "status": clarification.status.value,
        "due_date": clarification.due_date,
        "created_at": clarification.created_at
    }


@router.get("/applications/{application_id}/clarifications", response_model=List[ClarificationResponse])
def list_application_clarifications(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    clarifications = db.query(ClarificationRequest).filter(
        ClarificationRequest.application_id == application_id
    ).order_by(ClarificationRequest.created_at.desc()).all()

    results = []
    for c in clarifications:
        doc_title = c.relevant_document.title if c.relevant_document else None
        results.append({
            "id": c.id,
            "application_id": c.application_id,
            "application_ref": app.reference_no,
            "officer_name": c.requesting_officer.full_name if c.requesting_officer else "Officer",
            "subject": c.subject,
            "requested_information": c.requested_information,
            "instructions_for_correction": c.instructions_for_correction,
            "relevant_finding_id": c.relevant_finding_id,
            "relevant_document_id": c.relevant_document_id,
            "relevant_document_title": doc_title,
            "status": c.status.value,
            "due_date": c.due_date,
            "created_at": c.created_at
        })
    return results


@router.post("/clarifications/{clarification_id}/correction")
def submit_clarification_correction(
    clarification_id: int,
    explanation: str = Form(...),
    document_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Institution uploads corrected document (Version 2, 3), keeping historical versions intact.
    Strictly verifies institution membership, file size (< 25MB), and valid regulatory file types.
    """
    clarification = db.query(ClarificationRequest).filter(ClarificationRequest.id == clarification_id).first()
    if not clarification:
        raise HTTPException(status_code=404, detail="Clarification request not found")

    # Authorization verification: Ensure user belongs to the institution
    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id,
            InstitutionMembership.institution_id == clarification.application.institution_id
        ).first()
        if not membership and clarification.application.submitting_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied. You can only submit corrections for your own institution's applications."
            )

    safe_ext = os.path.splitext(file.filename)[1].lower() or ".pdf"
    allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg"}
    if safe_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format '{safe_ext}'. Only PDF and image documents (.pdf, .png, .jpg, .jpeg) are accepted."
        )

    contents = file.file.read()
    file_size = len(contents)
    max_size = 25 * 1024 * 1024  # 25 MB
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum permitted size of 25MB (uploaded size: {file_size / (1024 * 1024):.2f}MB)."
        )
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Cannot upload an empty file.")

    file_hash = OCREngine.calculate_file_hash(contents)
    storage_filename = f"{uuid.uuid4().hex}{safe_ext}"
    storage_path = os.path.join(settings.UPLOAD_DIR, storage_filename)

    with open(storage_path, "wb") as f_out:
        f_out.write(contents)

    service = RevalidationService(db)
    correction = service.submit_correction(
        clarification_request_id=clarification_id,
        submitting_user=current_user,
        explanation=explanation,
        document_id=document_id,
        file_path=storage_path,
        original_filename=file.filename,
        file_hash=file_hash,
        mime_type=file.content_type or "application/pdf",
        file_size_bytes=file_size
    )

    return {
        "message": "Corrected evidence uploaded successfully and queued for revalidation",
        "correction_id": correction.id,
        "application_status": clarification.application.status.value
    }


@router.post("/applications/{application_id}/revalidate", response_model=ValidationRunResponse)
def trigger_selective_revalidation(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Executes change-aware selective revalidation (Stage 13).
    Reruns affected checks, preserves history, updates resolution states.
    """
    service = RevalidationService(db)
    val_run = service.execute_change_aware_revalidation(
        application_id=application_id,
        triggering_user=current_user,
        reason=f"Selective revalidation triggered by {current_user.full_name}"
    )

    from app.api.v1.validation import get_validation_run_detail
    return get_validation_run_detail(val_run.id, current_user, db)

