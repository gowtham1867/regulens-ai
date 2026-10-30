import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from app.database import Base


class DocumentValidityStatus(str, enum.Enum):
    VALID = "VALID"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    RENEWAL_REQUESTED = "RENEWAL_REQUESTED"
    RENEWAL_SUBMITTED = "RENEWAL_SUBMITTED"


class DocumentValidityRecord(Base):
    __tablename__ = "document_validity_records"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    
    document_type = Column(String(64), nullable=False)  # LEASE_DEED, FIRE_SAFETY_NOC, BUILDING_SAFETY, AFFILIATION
    document_name = Column(String(255), nullable=False)
    issuing_authority = Column(String(255), nullable=False)
    
    issue_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=False, index=True)
    validity_years = Column(Float, nullable=True)
    
    status = Column(String(32), default=DocumentValidityStatus.VALID.value, nullable=False, index=True)
    days_remaining = Column(Integer, nullable=True)
    
    obligation_id = Column(Integer, ForeignKey("obligations.id"), nullable=True)
    renewal_requested_at = Column(DateTime, nullable=True)
    renewal_submitted_at = Column(DateTime, nullable=True)
    renewal_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    
    ocr_extracted = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    institution = relationship("Institution", backref="document_validities")
    document = relationship("Document", foreign_keys=[document_id])
    renewal_document = relationship("Document", foreign_keys=[renewal_document_id])
    obligation = relationship("Obligation", foreign_keys=[obligation_id])
