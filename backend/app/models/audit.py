import hashlib
import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_email = Column(String(255), default="SYSTEM", nullable=False)
    actor_role = Column(String(50), default="SYSTEM", nullable=False)
    
    action = Column(String(100), index=True, nullable=False)
    entity_type = Column(String(100), index=True, nullable=False)
    entity_id = Column(String(100), nullable=False)
    
    ip_address = Column(String(50), nullable=True)
    correlation_id = Column(String(100), nullable=True)
    
    before_state = Column(Text, nullable=True)  # JSON
    after_state = Column(Text, nullable=True)   # JSON
    details = Column(Text, nullable=True)
    
    # Hash-linked audit chain for tamper-evidence (Section 15)
    previous_hash = Column(String(64), nullable=True)
    entry_hash = Column(String(64), nullable=False)

    actor = relationship("User", back_populates="audit_events")

    @classmethod
    def calculate_hash(cls, timestamp: datetime, actor_email: str, action: str, entity_type: str, entity_id: str, prev_hash: str) -> str:
        payload = f"{timestamp.isoformat()}|{actor_email}|{action}|{entity_type}|{entity_id}|{prev_hash or 'GENESIS'}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

