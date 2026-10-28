import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    INSTITUTION_USER = "INSTITUTION_USER"
    AICTE_OFFICER = "AICTE_OFFICER"
    ADMINISTRATOR = "ADMINISTRATOR"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.INSTITUTION_USER)
    designation = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    institution_memberships = relationship("InstitutionMembership", back_populates="user", cascade="all, delete-orphan")
    reviewed_applications = relationship("OfficerReview", back_populates="officer")
    decisions = relationship("WorkflowDecision", back_populates="officer")
    audit_events = relationship("AuditEvent", back_populates="actor")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

