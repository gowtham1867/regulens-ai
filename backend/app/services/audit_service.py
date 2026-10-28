import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.audit import AuditEvent
from app.models.user import User


def record_audit_event(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str,
    actor: Optional[User] = None,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> AuditEvent:
    now = datetime.utcnow()
    
    # Retrieve latest audit event for hash chain link
    last_event = db.query(AuditEvent).order_by(desc(AuditEvent.id)).first()
    prev_hash = last_event.entry_hash if last_event else "GENESIS_BLOCK_REGULENS_AI"
    
    actor_email = actor.email if actor else "SYSTEM"
    actor_role = actor.role.value if actor else "SYSTEM"
    actor_id = actor.id if actor else None
    
    entry_hash = AuditEvent.calculate_hash(
        timestamp=now,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        prev_hash=prev_hash
    )
    
    event = AuditEvent(
        timestamp=now,
        actor_id=actor_id,
        actor_email=actor_email,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        ip_address=ip_address,
        correlation_id=correlation_id,
        before_state=json.dumps(before_state, default=str) if before_state else None,
        after_state=json.dumps(after_state, default=str) if after_state else None,
        details=details,
        previous_hash=prev_hash,
        entry_hash=entry_hash
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def verify_audit_chain_integrity(db: Session) -> Dict[str, Any]:
    events: List[AuditEvent] = db.query(AuditEvent).order_by(AuditEvent.id).all()
    if not events:
        return {"status": "EMPTY", "valid": True, "total_events": 0, "broken_at_id": None}
    
    prev_hash = "GENESIS_BLOCK_REGULENS_AI"
    for event in events:
        expected_hash = AuditEvent.calculate_hash(
            timestamp=event.timestamp,
            actor_email=event.actor_email,
            action=event.action,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            prev_hash=prev_hash
        )
        if event.entry_hash != expected_hash or event.previous_hash != prev_hash:
            return {
                "status": "TAMPERED",
                "valid": False,
                "total_events": len(events),
                "broken_at_id": event.id,
                "broken_at_timestamp": event.timestamp.isoformat(),
                "action": event.action
            }
        prev_hash = event.entry_hash
        
    return {
        "status": "VALID",
        "valid": True,
        "total_events": len(events),
        "latest_hash": prev_hash,
        "verified_at": datetime.utcnow().isoformat()
    }

