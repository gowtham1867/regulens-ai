from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.document_validity import DocumentValidityRecord, DocumentValidityStatus
from app.models.institution import Institution
from app.models.obligation import Obligation, ObligationType, ResponsibleRole
from app.models.document import Document
from app.models.user import User
from app.services.obligation_service import create_obligation
from app.services.clock_engine import ClockEngine
from app.services.audit_service import record_audit_event


class DocumentValidityService:
    @classmethod
    def register_or_update_validity(
        cls,
        db: Session,
        institution_id: int,
        document_type: str,
        document_name: str,
        issuing_authority: str,
        expiry_date: datetime,
        document_id: Optional[int] = None,
        issue_date: Optional[datetime] = None,
        validity_years: Optional[float] = None,
        ocr_extracted: bool = True
    ) -> DocumentValidityRecord:
        now = datetime.utcnow()
        days_remaining = (expiry_date - now).days

        if days_remaining <= 0:
            status = DocumentValidityStatus.EXPIRED.value
        elif days_remaining <= 90:
            status = DocumentValidityStatus.EXPIRING_SOON.value
        else:
            status = DocumentValidityStatus.VALID.value

        record = db.query(DocumentValidityRecord).filter(
            DocumentValidityRecord.institution_id == institution_id,
            DocumentValidityRecord.document_type == document_type
        ).first()

        if not record:
            record = DocumentValidityRecord(
                institution_id=institution_id,
                document_id=document_id,
                document_type=document_type,
                document_name=document_name,
                issuing_authority=issuing_authority,
                issue_date=issue_date,
                expiry_date=expiry_date,
                validity_years=validity_years,
                status=status,
                days_remaining=days_remaining,
                ocr_extracted=ocr_extracted
            )
            db.add(record)
            db.flush()
        else:
            record.document_id = document_id or record.document_id
            record.document_name = document_name
            record.issuing_authority = issuing_authority
            record.expiry_date = expiry_date
            record.status = status
            record.days_remaining = days_remaining
            record.updated_at = now

        # If expiring soon or expired, ensure an obligation exists in Promise Ledger
        if status in [DocumentValidityStatus.EXPIRING_SOON.value, DocumentValidityStatus.EXPIRED.value] and not record.obligation_id:
            inst = db.query(Institution).filter(Institution.id == institution_id).first()
            inst_name = inst.name if inst else f"Institution {institution_id}"
            
            obl = create_obligation(
                db=db,
                institution_id=institution_id,
                obligation_type=ObligationType.LEASE_RENEWAL.value if "LEASE" in document_type else ObligationType.DOCUMENT_SUBMISSION.value,
                title=f"Statutory Renewal Required: {document_name}",
                description=f"{document_type} issued by {issuing_authority} expires on {expiry_date.strftime('%d-%b-%Y')}. Submit renewed certificate before approval.",
                responsible_entity=inst_name,
                responsible_role=ResponsibleRole.INSTITUTION.value,
                responsible_post="Head of Institution / Registrar",
                source_event="DOCUMENT_EXPIRY_MONITOR",
                aph_clause="APH 2024-27 Clause 4.1",
                configured_days=max(7, min(30, days_remaining if days_remaining > 0 else 7)),
                deadline_type="CALENDAR_DAYS"
            )
            record.obligation_id = obl.id

        db.commit()
        db.refresh(record)
        return record

    @classmethod
    def submit_renewal(
        cls,
        db: Session,
        record_id: int,
        renewal_document_id: int,
        new_expiry_date: datetime,
        institution_user: User
    ) -> DocumentValidityRecord:
        record = db.query(DocumentValidityRecord).filter(DocumentValidityRecord.id == record_id).first()
        if not record:
            raise ValueError(f"Record {record_id} not found.")

        now = datetime.utcnow()
        days_rem = (new_expiry_date - now).days
        record.renewal_document_id = renewal_document_id
        record.renewal_submitted_at = now
        record.expiry_date = new_expiry_date
        record.days_remaining = days_rem
        record.status = DocumentValidityStatus.RENEWAL_SUBMITTED.value
        record.updated_at = now

        if record.obligation_id:
            ClockEngine.complete_obligation(
                db=db,
                obligation_id=record.obligation_id,
                reason="Institution uploaded renewed statutory certificate.",
                actor=institution_user.email
            )

        db.commit()
        db.refresh(record)
        return record
