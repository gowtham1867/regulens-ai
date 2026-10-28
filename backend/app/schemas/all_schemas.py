from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr


# --- AUTH ---
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
    full_name: str
    email: str
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None
    approval_status: Optional[str] = "APPROVED"


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    # Account Administrator Information
    email: str
    password: str
    full_name: str
    designation: Optional[str] = "Authorized Signatory / Registrar"
    phone: Optional[str] = None

    # Institution Information
    institution_name: str
    aicte_id: Optional[str] = None
    institution_type: Optional[str] = "ENGINEERING_AND_TECHNOLOGY"
    address: Optional[str] = "Campus Address"
    state: Optional[str] = "Delhi"
    district: Optional[str] = "New Delhi"
    pin_code: Optional[str] = "110001"
    institution_email: Optional[str] = None
    contact_phone: Optional[str] = None

    # Baseline Claims
    approved_intake: Optional[int] = 300
    land_area_acres: Optional[float] = 5.0


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    designation: Optional[str] = None
    is_active: bool
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- INSTITUTION ---
class InstitutionResponse(BaseModel):
    id: int
    aicte_id: str
    name: str
    address: str
    state: str
    district: str
    pin_code: str
    institution_type: str
    established_year: Optional[int] = None
    approval_status: str
    contact_email: str
    contact_phone: Optional[str] = None
    approved_intake: int
    land_area_acres: str

    class Config:
        from_attributes = True


# --- APPLICATION ---
class ApplicationCreate(BaseModel):
    title: str
    category: str = "EXTENSION_OF_APPROVAL"
    academic_year: str = "2025-2026"
    declared_intake: Optional[int] = 300
    declared_land_acres: Optional[float] = 10.5
    declared_built_up_sqm: Optional[float] = 8500.0
    notes: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    reference_no: str
    institution_id: int
    institution_name: Optional[str] = None
    title: str
    category: str
    academic_year: str
    status: str
    declared_intake: Optional[int] = None
    declared_land_acres: Optional[float] = None
    declared_built_up_sqm: Optional[float] = None
    is_demo_seed: bool = False
    submission_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    assigned_officer_name: Optional[str] = None
    findings_count: Optional[int] = 0
    highest_severity: Optional[str] = None

    class Config:
        from_attributes = True


# --- DOCUMENT & OCR ---
class ExtractedFieldResponse(BaseModel):
    id: int
    field_key: str
    field_label: str
    extracted_value: str
    normalized_value: Optional[str] = None
    source_page: int
    confidence: float
    is_manually_corrected: bool
    corrected_value: Optional[str] = None
    correction_reason: Optional[str] = None

    class Config:
        from_attributes = True


class FieldCorrectionRequest(BaseModel):
    corrected_value: str
    reason: str


class DocumentVersionResponse(BaseModel):
    id: int
    version_number: int
    original_filename: str
    file_hash: str
    mime_type: str
    file_size_bytes: int
    page_count: int
    status: str
    error_message: Optional[str] = None
    ocr_confidence: Optional[float] = None
    created_at: datetime
    extracted_fields: List[ExtractedFieldResponse] = []

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    id: int
    application_id: int
    document_type: str
    title: str
    is_required: bool
    created_at: datetime
    latest_version: Optional[DocumentVersionResponse] = None
    all_versions_count: int = 0

    class Config:
        from_attributes = True


# --- RULES & FINDINGS ---
class RegulatoryRuleResponse(BaseModel):
    id: int
    rule_code: str
    title: str
    description: str
    category: str
    severity: str
    evaluation_method: str
    is_illustrative: bool
    official_source_ref: str
    is_active: bool

    class Config:
        from_attributes = True


class ValidationFindingResponse(BaseModel):
    id: int
    rule_code: str
    rule_title: str
    category: str
    status: str
    severity: str
    affected_claim_field: Optional[str] = None
    affected_document_version_id: Optional[int] = None
    document_title: Optional[str] = None
    expected_value: Optional[str] = None
    observed_value: Optional[str] = None
    explanation: str
    recommended_action: Optional[str] = None
    source_page: Optional[int] = None
    is_active: bool
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ValidationRunResponse(BaseModel):
    id: int
    run_number: int
    trigger_type: str
    triggering_change: Optional[str] = None
    total_rules_evaluated: int
    passed_count: int
    failed_count: int
    warning_count: int
    manual_review_count: int
    reused_checks_count: int
    executed_at: datetime
    findings: List[ValidationFindingResponse] = []

    class Config:
        from_attributes = True


# --- ISSUER VERIFICATION ---
class VerificationSourceResponse(BaseModel):
    id: int
    source_code: str
    name: str
    authority_type: str
    verification_method: str
    is_simulated: bool
    simulated_badge_label: str
    is_available: bool

    class Config:
        from_attributes = True


class VerificationAttemptResponse(BaseModel):
    id: int
    source_name: str
    authority_type: str
    certificate_number: Optional[str] = None
    verification_method: str
    outcome: str
    is_reused: bool
    is_simulated: bool
    failure_reason: Optional[str] = None
    evidence_payload: Optional[str] = None
    request_timestamp: datetime
    response_timestamp: datetime

    class Config:
        from_attributes = True


class ManualVerificationRequest(BaseModel):
    outcome: str = "VERIFIED"  # "VERIFIED", "MISMATCH_DETECTED", "MANUAL_REVIEW_REQUIRED"
    notes: str
    issuing_authority: Optional[str] = None
    certificate_number: Optional[str] = None


# --- WORKFLOW ---
class ClarificationRequestCreate(BaseModel):
    subject: str
    requested_information: str
    instructions_for_correction: str
    relevant_finding_id: Optional[int] = None
    relevant_document_id: Optional[int] = None
    due_days: Optional[int] = 7


class ClarificationResponse(BaseModel):
    id: int
    application_id: int
    application_ref: str
    officer_name: str
    subject: str
    requested_information: str
    instructions_for_correction: str
    relevant_finding_id: Optional[int] = None
    relevant_document_id: Optional[int] = None
    relevant_document_title: Optional[str] = None
    status: str
    due_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OfficerReviewCreate(BaseModel):
    review_stage: str = "SCRUTINY_REVIEW"
    review_notes: str
    recommended_action: str  # APPROVE, RETURN, REJECT, REQUEST_CLARIFICATION


class WorkflowDecisionCreate(BaseModel):
    decision: str  # APPROVE, RETURN, REJECT, REQUEST_CORRECTION, REQUEST_DOCUMENTS, UNDER_REVIEW
    justification: str
    rejection_reason: Optional[str] = None  # Required if decision == "REJECT"
    rule_ids: Optional[List[int]] = None
    document_ids: Optional[List[int]] = None
    is_override: bool = False
    override_reason: Optional[str] = None


class WorkflowDecisionResponse(BaseModel):
    id: int
    decision: str
    justification: str
    officer_name: str
    rejection_reason: Optional[str] = None
    is_override: bool
    override_reason: Optional[str] = None
    decided_at: datetime

    class Config:
        from_attributes = True


# --- AUDIT & NOTIFICATION ---
class AuditEventResponse(BaseModel):
    id: int
    timestamp: datetime
    actor_email: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    details: Optional[str] = None
    entry_hash: str
    previous_hash: Optional[str] = None

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    notification_type: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime
    application_id: Optional[int] = None
    institution_id: Optional[int] = None
    action_type: Optional[str] = None
    details: Optional[str] = None

    class Config:
        from_attributes = True

