from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.document_validity import DocumentValidityRecord, DocumentValidityStatus
from app.models.institution import InstitutionMembership
from app.services.document_validity_service import DocumentValidityService
from app.services.explanation_service import ExplanationService

router = APIRouter(prefix="/document-validity", tags=["Document Validity & Expiry Monitoring"])


class RegisterValidityRequest(BaseModel):
    institution_id: int
    document_type: str
    document_name: str
    issuing_authority: str
    expiry_date: datetime
    document_id: Optional[int] = None
    issue_date: Optional[datetime] = None
    validity_years: Optional[float] = None


class SubmitRenewalRequest(BaseModel):
    renewal_document_id: int
    new_expiry_date: datetime


@router.get("")
def list_validity_records(
    institution_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(DocumentValidityRecord)

    if current_user.role == UserRole.INSTITUTION_USER:
        membership = db.query(InstitutionMembership).filter(
            InstitutionMembership.user_id == current_user.id
        ).first()
        if not membership:
            return []
        query = query.filter(DocumentValidityRecord.institution_id == membership.institution_id)
    elif institution_id:
        query = query.filter(DocumentValidityRecord.institution_id == institution_id)

    if status_filter:
        query = query.filter(DocumentValidityRecord.status == status_filter)

    records = query.order_by(DocumentValidityRecord.expiry_date.asc()).all()
    now = datetime.utcnow()

    results = []
    for r in records:
        days_rem = (r.expiry_date - now).days
        results.append({
            "id": r.id,
            "institution_id": r.institution_id,
            "institution_name": r.institution.name if r.institution else "N/A",
            "document_id": r.document_id,
            "document_type": r.document_type,
            "document_name": r.document_name,
            "issuing_authority": r.issuing_authority,
            "issue_date": r.issue_date.isoformat() if r.issue_date else None,
            "expiry_date": r.expiry_date.isoformat(),
            "validity_years": r.validity_years,
            "status": r.status,
            "days_remaining": days_rem,
            "obligation_id": r.obligation_id,
            "renewal_submitted_at": r.renewal_submitted_at.isoformat() if r.renewal_submitted_at else None,
            "ocr_extracted": r.ocr_extracted
        })
    return results


@router.get("/{record_id}/why")
def explain_validity_why(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        return ExplanationService.explain_document_validity(db, record_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", status_code=status.HTTP_201_CREATED)
def register_validity(
    req: RegisterValidityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record = DocumentValidityService.register_or_update_validity(
        db=db,
        institution_id=req.institution_id,
        document_type=req.document_type,
        document_name=req.document_name,
        issuing_authority=req.issuing_authority,
        expiry_date=req.expiry_date,
        document_id=req.document_id,
        issue_date=req.issue_date,
        validity_years=req.validity_years
    )
    return {"status": "REGISTERED", "record_id": record.id, "computed_status": record.status}


@router.post("/{record_id}/renew")
def renew_document(
    record_id: int,
    req: SubmitRenewalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        record = DocumentValidityService.submit_renewal(
            db=db,
            record_id=record_id,
            renewal_document_id=req.renewal_document_id,
            new_expiry_date=req.new_expiry_date,
            institution_user=current_user
        )
        return {"status": "RENEWAL_SUBMITTED", "new_expiry_date": record.expiry_date.isoformat()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
