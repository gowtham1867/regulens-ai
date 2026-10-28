export type UserRole = "INSTITUTION_USER" | "AICTE_OFFICER" | "ADMINISTRATOR";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  designation?: string;
  is_active: boolean;
  institution_id?: number;
  institution_name?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface Application {
  id: number;
  reference_no: string;
  institution_id: number;
  institution_name: string;
  title: string;
  category: string;
  academic_year: string;
  status: string;
  declared_intake?: number;
  declared_land_acres?: number;
  declared_built_up_sqm?: number;
  is_demo_seed: boolean;
  submission_date?: string;
  created_at: string;
  updated_at: string;
  assigned_officer_name?: string;
  findings_count: number;
  highest_severity?: "CRITICAL" | "MAJOR" | "MINOR" | "INFO";
}

export interface ExtractedField {
  id: number;
  field_key: string;
  field_label: string;
  extracted_value: string;
  normalized_value?: string;
  source_page: number;
  confidence: number;
  is_manually_corrected: boolean;
  corrected_value?: string;
  correction_reason?: string;
}

export interface DocumentVersion {
  id: number;
  version_number: number;
  original_filename: string;
  file_hash: string;
  mime_type: string;
  file_size_bytes: number;
  page_count: number;
  status: string;
  error_message?: string;
  ocr_confidence?: number;
  created_at: string;
  extracted_fields: ExtractedField[];
}

export interface DocumentItem {
  id: number;
  application_id: number;
  document_type: string;
  title: string;
  is_required: boolean;
  created_at: string;
  latest_version?: DocumentVersion;
  all_versions_count: number;
}

export interface ValidationFinding {
  id: number;
  rule_code: string;
  rule_title: string;
  category: string;
  status: "PASSED" | "FAILED" | "WARNING" | "MANUAL_REVIEW_REQUIRED" | "PENDING_VERIFICATION" | "SUPERSEDED" | "RESOLVED";
  severity: "CRITICAL" | "MAJOR" | "MINOR" | "INFO";
  affected_claim_field?: string;
  affected_document_version_id?: number;
  document_title?: string;
  expected_value?: string;
  observed_value?: string;
  explanation: string;
  recommended_action?: string;
  source_page?: number;
  is_active: boolean;
  is_resolved: boolean;
  created_at: string;
}

export interface VerificationSource {
  id: number;
  source_code: string;
  name: string;
  authority_type: string;
  verification_method: string;
  is_simulated: boolean;
  simulated_badge_label: string;
  is_available: boolean;
}

export interface VerificationAttempt {
  id: number;
  source_name: string;
  authority_type: string;
  certificate_number?: string;
  verification_method: string;
  outcome: string;
  is_reused: boolean;
  is_simulated: boolean;
  failure_reason?: string;
  evidence_payload?: string;
  request_timestamp: string;
  response_timestamp: string;
}

export interface Clarification {
  id: number;
  application_id: number;
  application_ref: string;
  officer_name: string;
  subject: string;
  requested_information: string;
  instructions_for_correction: string;
  relevant_finding_id?: number;
  relevant_document_id?: number;
  relevant_document_title?: string;
  status: "OPEN" | "RESPONDED" | "RESOLVED" | "EXPIRED";
  due_date?: string;
  created_at: string;
}

export interface TrustGraphNode {
  id: string;
  label: string;
  type: string;
  tier: number;
  status: string;
  metadata: Record<string, any>;
}

export interface TrustGraphEdge {
  source: string;
  target: string;
  label: string;
  type: string;
  confidence?: number;
}

export interface ContradictoryClaim {
  id: string;
  category: string;
  title: string;
  severity: "CRITICAL" | "MAJOR" | "WARNING" | "INFO";
  claim_label: string;
  claim_value: string;
  evidence_label: string;
  evidence_value: string;
  discrepancy_delta: string;
  explanation: string;
  suggested_action: string;
}

export interface DuplicateCandidate {
  id: string;
  document_id: number;
  document_title: string;
  file_hash: string;
  matched_version_id: number;
  matched_application_ref: string;
  matched_institution_name: string;
  is_cross_institution: boolean;
  similarity_score: number;
  severity: string;
  description: string;
}

export interface RelationshipTriplet {
  source_id: string;
  source_label: string;
  source_type: string;
  source_tier: number;
  relation: string;
  target_id: string;
  target_label: string;
  target_type: string;
  target_tier: number;
  edge_type: string;
  confidence: number;
}

export interface ExtractedClaimItem {
  field_id: number;
  document_id: number;
  document_title: string;
  document_type: string;
  version: string;
  field_key: string;
  field_label: string;
  extracted_value: string;
  normalized_value: string;
  confidence: number;
  source_page: number;
  is_manually_corrected: boolean;
  corrected_value?: string;
  correction_reason?: string;
}

export interface TrustGraphData {
  application_id: number;
  reference_no: string;
  institution_name?: string;
  nodes: TrustGraphNode[];
  edges: TrustGraphEdge[];
  finding_paths?: Record<string, string[]>;
  contradictory_claims?: ContradictoryClaim[];
  duplicate_candidates?: DuplicateCandidate[];
  relationship_table?: RelationshipTriplet[];
  extracted_claims?: ExtractedClaimItem[];
  summary: {
    total_nodes: number;
    total_edges: number;
    tier_0_count?: number;
    tier_1_count?: number;
    tier_2_count?: number;
    tier_3_count?: number;
    tier_4_count?: number;
    findings_count: number;
    contradictions_count?: number;
    duplicates_count?: number;
  };
}

export interface AuditEvent {
  id: number;
  timestamp: string;
  actor_email: string;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details?: string;
  entry_hash: string;
  previous_hash?: string;
}

export interface TestCaseResult {
  test_id: string;
  scenario: string;
  expected_outcome: string;
  actual_outcome: string;
  passed: boolean;
}

export interface BenchmarkReport {
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  pass_rate_percentage: number;
  execution_time_seconds: number;
  test_cases: TestCaseResult[];
  evaluated_at: string;
}

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  notification_type: string;
  link?: string;
  is_read: boolean;
  created_at: string;
  application_id?: number;
  institution_id?: number;
  action_type?: string;
  details?: string;
}

export interface ChecklistRequirementItem {
  requirement_id: number;
  document_type: string;
  title: string;
  description: string;
  is_mandatory: boolean;
  accepted_formats: string;
  required_fields: string[];
  validation_criteria?: string;
  source_clause?: string;
  status: "SATISFIED" | "MISSING" | "EXPIRED" | "MISSING_INFORMATION" | "DEFICIENT" | "NOT_SUBMITTED" | "PENDING";
  submitted_document_id?: number;
  latest_version_id?: number;
  latest_filename?: string;
  latest_version_number?: number;
  ocr_status?: string;
  missing_fields?: string[];
  reason?: string;
  required_action?: string;
}

export interface ApplicationRequirementsSummary {
  application_id: number;
  reference_no: string;
  category: string;
  checklist_title: string;
  academic_year: string;
  total_requirements: number;
  mandatory_requirements: number;
  satisfied_mandatory: number;
  completion_percentage: number;
  can_submit: boolean;
  open_deficiencies_count: number;
  items: ChecklistRequirementItem[];
}

export interface ApplicationDeficiencyItem {
  id: number;
  rule_code: string;
  document_type?: string;
  deficiency_type: string;
  severity: "CRITICAL" | "MAJOR" | "MINOR" | "INFO";
  title: string;
  description: string;
  reason: string;
  required_action: string;
  status: "OPEN" | "RESOLVED" | "WAIVED" | "SUPERSEDED";
  affected_document_version_id?: number;
  resolved_by_document_version_id?: number;
  resolution_notes?: string;
  created_at: string;
  resolved_at?: string;
}

export interface DuplicateRecordItem {
  id: number;
  document_version_id: number;
  matched_document_version_id: number;
  match_type: "EXACT_HASH" | "CERTIFICATE_NUMBER" | "TEXT_SIMILARITY" | "SURVEY_NUMBER";
  similarity_score: number;
  matched_identifier?: string;
  explanation: string;
  status: "DETECTED" | "LEGITIMATE_REUSE" | "CONFIRMED_DUPLICATE" | "DISMISSED";
  officer_resolution_notes?: string;
  resolved_at?: string;
  created_at: string;
  matched_filename: string;
  matched_app_ref: string;
  matched_institution: string;
}
