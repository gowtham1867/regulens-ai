from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.audit import AuditEvent
from app.schemas.all_schemas import AuditEventResponse
from app.services.audit_service import verify_audit_chain_integrity

router = APIRouter(tags=["Audit Trail"])


@router.get("/audit-events", response_model=List[AuditEventResponse])
def list_audit_events(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only officers and admins can inspect global audit logs
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Audit trail access restricted to authorized personnel")

    query = db.query(AuditEvent)
    if action:
        query = query.filter(AuditEvent.action == action)
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditEvent.entity_id == entity_id)

    events = query.order_by(desc(AuditEvent.id)).limit(limit).all()
    return events


@router.get("/audit-integrity")
def check_audit_integrity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verifies cryptographic SHA-256 hash chaining of all persistent audit events (Section 15).
    """
    if current_user.role not in [UserRole.AICTE_OFFICER, UserRole.ADMINISTRATOR]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    integrity_report = verify_audit_chain_integrity(db)
    return integrity_report

