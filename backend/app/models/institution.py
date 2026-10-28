from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    aicte_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    address = Column(Text, nullable=False)
    state = Column(String(100), nullable=False)
    district = Column(String(100), nullable=False)
    pin_code = Column(String(20), nullable=False)
    institution_type = Column(String(100), default="ENGINEERING_AND_TECHNOLOGY")
    established_year = Column(Integer, nullable=True)
    approval_status = Column(String(50), default="APPROVED")
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Baseline claims for cross-document consistency checks
    approved_intake = Column(Integer, default=300)
    land_area_acres = Column(String(50), default="10.5")

    # Relationships
    memberships = relationship("InstitutionMembership", back_populates="institution", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="institution")


class InstitutionMembership(Base):
    __tablename__ = "institution_memberships"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    is_primary_contact = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="institution_memberships")
    institution = relationship("Institution", back_populates="memberships")

