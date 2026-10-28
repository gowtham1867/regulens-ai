import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ShieldCheck,
  Network,
  Download,
  Upload,
  RefreshCw,
  PlusCircle,
  FileCheck,
  Eye,
  Edit2,
  FileDown,
  Layers,
  History,
  AlertCircle,
  CheckSquare,
  ListChecks,
  Copy,
  ShieldAlert,
  Clock,
  ArrowRight,
  Info
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { StatusBadge } from "../components/common/StatusBadge";
import { SimulatedBadge } from "../components/common/SimulatedBadge";
import { TrustGraphViewer } from "../components/trustgraph/TrustGraphViewer";
import { DocumentPreviewModal } from "../components/documents/DocumentPreviewModal";
import { AuthorityVerificationModal } from "../components/documents/AuthorityVerificationModal";
import type {
  Application,
  DocumentItem,
  ValidationFinding,
  VerificationAttempt,
  Clarification,
  TrustGraphData,
  ExtractedField,
  ApplicationRequirementsSummary,
  ChecklistRequirementItem,
  ApplicationDeficiencyItem,
  DuplicateRecordItem
} from "../types";

export const ApplicationDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const appId = parseInt(id || "1", 10);
  const { user } = useAuth();
  const isOfficerOrAdmin = user?.role === "AICTE_OFFICER" || user?.role === "ADMINISTRATOR";

  const [app, setApp] = useState<Application | null>(null);
  const [activeTab, setActiveTab] = useState<"checklist" | "documents" | "deficiencies" | "anomalies" | "findings" | "verification" | "trustgraph" | "clarifications" | "reviews">("checklist");
  const [loading, setLoading] = useState(true);

  // Data states
  const [requirementsData, setRequirementsData] = useState<ApplicationRequirementsSummary | null>(null);
  const [deficiencies, setDeficiencies] = useState<ApplicationDeficiencyItem[]>([]);
  const [duplicates, setDuplicates] = useState<DuplicateRecordItem[]>([]);
  const [findings, setFindings] = useState<ValidationFinding[]>([]);
  const [includeHistoric, setIncludeHistoric] = useState(false);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [clarifications, setClarifications] = useState<Clarification[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [decisions, setDecisions] = useState<any[]>([]);
  const [trustGraph, setTrustGraph] = useState<TrustGraphData | null>(null);

  // Modals state
  const [showClarificationModal, setShowClarificationModal] = useState(false);
  const [showCorrectionModal, setShowCorrectionModal] = useState(false);
  const [selectedClarificationId, setSelectedClarificationId] = useState<number | null>(null);
  const [showDecisionModal, setShowDecisionModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showCorrectFieldModal, setShowCorrectFieldModal] = useState(false);
  const [selectedField, setSelectedField] = useState<ExtractedField | null>(null);

  // Deficiency & Duplicate Resolution Modals
  const [showResolveDeficiencyModal, setShowResolveDeficiencyModal] = useState(false);
  const [selectedDeficiency, setSelectedDeficiency] = useState<ApplicationDeficiencyItem | null>(null);
  const [deficiencyResolutionNotes, setDeficiencyResolutionNotes] = useState("");

  const [showResolveDuplicateModal, setShowResolveDuplicateModal] = useState(false);
  const [selectedDuplicate, setSelectedDuplicate] = useState<DuplicateRecordItem | null>(null);
  const [duplicateStatusVal, setDuplicateStatusVal] = useState<string>("LEGITIMATE_REUSE");
  const [duplicateResolutionNotes, setDuplicateResolutionNotes] = useState("");

  // Action forms
  const [clarSubject, setClarSubject] = useState("");
  const [clarReqInfo, setClarReqInfo] = useState("");
  const [clarInstructions, setClarInstructions] = useState("");

  const [corrExplanation, setCorrExplanation] = useState("");
  const [corrDocumentId, setCorrDocumentId] = useState<number>(0);
  const [corrFile, setCorrFile] = useState<File | null>(null);

  const [decisionType, setDecisionType] = useState<"APPROVE" | "REJECT" | "REQUEST_CORRECTION" | "REQUEST_DOCUMENTS" | "UNDER_REVIEW">("APPROVE");
  const [rejectionReason, setRejectionReason] = useState<string>("Critical Safety Compliance Shortfall (Expired / Invalid Fire NOC)");
  const [customRejectionReason, setCustomRejectionReason] = useState<string>("");
  const [decisionJustification, setDecisionJustification] = useState("");
  const [selectedFindingRuleIds, setSelectedFindingRuleIds] = useState<number[]>([]);
  const [selectedAffectedDocIds, setSelectedAffectedDocIds] = useState<number[]>([]);
  const [decisionOverride, setDecisionOverride] = useState(false);
  const [decisionOverrideReason, setDecisionOverrideReason] = useState("");
  const [confirmStep, setConfirmStep] = useState(false);

  const [correctedValue, setCorrectedValue] = useState("");
  const [correctionReason, setCorrectionReason] = useState("");

  const [uploadDocType, setUploadDocType] = useState<string>("FIRE_SAFETY_CERTIFICATE");
  const [uploadDocTitle, setUploadDocTitle] = useState<string>("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Document Preview Modal states
  const [previewDoc, setPreviewDoc] = useState<any>(null);
  const [previewVersion, setPreviewVersion] = useState<any>(null);
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  // Export progress states
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);

  // Authority Verification Modal states
  const [verifDoc, setVerifDoc] = useState<any>(null);
  const [verifVersion, setVerifVersion] = useState<any>(null);
  const [showVerifModal, setShowVerifModal] = useState(false);

  const handleOpenVerifyModal = (doc: any, v?: any) => {
    setVerifDoc(doc);
    const chosenV = v || (doc.versions && doc.versions.length > 0 ? doc.versions[doc.versions.length - 1] : null);
    setVerifVersion(chosenV);
    setShowVerifModal(true);
  };

  const handleOpenPreview = (doc: any, v: any) => {
    setPreviewDoc(doc);
    setPreviewVersion(v);
    setShowPreviewModal(true);
  };

  const handleDownloadDirect = async (v: any) => {
    try {
      const { blob, filename } = await api.downloadDocumentVersion(v.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || v.original_filename || "document";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || "Failed to download document");
    }
  };

  const handleExportPdf = async () => {
    setExportingPdf(true);
    try {
      const { blob, filename } = await api.exportPdf(appId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || `ReguLens_Scrutiny_${app?.reference_no || appId}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setActionMessage("Regulatory scrutiny PDF report generated and downloaded successfully.");
    } catch (err: any) {
      alert(err.message || "Failed to generate PDF report");
    } finally {
      setExportingPdf(false);
    }
  };

  const handleExportCsv = async () => {
    setExportingCsv(true);
    try {
      const { blob, filename } = await api.exportCsv(appId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || `ReguLens_Report_${app?.reference_no || appId}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setActionMessage("Comprehensive compliance scrutiny CSV exported successfully.");
    } catch (err: any) {
      alert(err.message || "Failed to generate CSV export");
    } finally {
      setExportingCsv(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, [appId, includeHistoric]);

  const loadAllData = async () => {
    setLoading(true);
    // 1. Fetch application master record first so the app view is resilient
    try {
      const appData = await api.getApplication(appId);
      setApp(appData);
    } catch (err: any) {
      console.error("Failed to load application master record:", err);
      setLoading(false);
      return;
    }

    // 2. Load secondary scrutiny datasets safely so an issue in any one doesn't crash the application
    try {
      const [fndRes, docRes, anomRes, clarRes, revRes, tgRes, reqRes, defRes, dupRes, decRes] =
        await Promise.allSettled([
          api.getFindings(appId, includeHistoric),
          api.getDocuments(appId),
          api.getAnomalies(appId),
          api.getClarifications(appId),
          api.getReviews(appId),
          api.getTrustGraph(appId),
          api.getRequirements(appId),
          api.getDeficiencies(appId),
          api.getDuplicates(appId),
          api.getDecisions(appId),
        ]);

      if (fndRes.status === "fulfilled") setFindings(fndRes.value || []);
      if (docRes.status === "fulfilled") setDocuments(docRes.value || []);
      if (anomRes.status === "fulfilled") setAnomalies(anomRes.value?.anomalies || []);
      if (clarRes.status === "fulfilled") setClarifications(clarRes.value || []);
      if (revRes.status === "fulfilled") setReviews(revRes.value || []);
      if (tgRes.status === "fulfilled") setTrustGraph(tgRes.value);
      if (reqRes.status === "fulfilled") setRequirementsData(reqRes.value);
      if (defRes.status === "fulfilled") setDeficiencies(defRes.value || []);
      if (dupRes.status === "fulfilled") setDuplicates(dupRes.value || []);
      if (decRes.status === "fulfilled") setDecisions(decRes.value || []);
    } catch (err) {
      console.error("Error loading secondary scrutiny datasets:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleRunValidation = async () => {
    setActionLoading(true);
    try {
      await api.runValidation(appId);
      setActionMessage("Validation engine executed successfully. Findings refreshed.");
      await loadAllData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolveDeficiency = async () => {
    if (!selectedDeficiency) return;
    setActionLoading(true);
    try {
      await api.resolveDeficiency(appId, selectedDeficiency.id, {
        status: "RESOLVED",
        resolution_notes: deficiencyResolutionNotes || "Manually resolved/waived by authorized official",
      });
      setShowResolveDeficiencyModal(false);
      setSelectedDeficiency(null);
      setDeficiencyResolutionNotes("");
      setActionMessage("Regulatory deficiency updated successfully.");
      await loadAllData();
    } catch (err: any) {
      alert(err.message || "Failed to resolve deficiency");
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolveDuplicate = async () => {
    if (!selectedDuplicate) return;
    setActionLoading(true);
    try {
      await api.resolveDuplicate(appId, selectedDuplicate.id, {
        status: duplicateStatusVal,
        officer_resolution_notes: duplicateResolutionNotes || "Reviewed by regulatory officer",
      });
      setShowResolveDuplicateModal(false);
      setSelectedDuplicate(null);
      setDuplicateResolutionNotes("");
      setActionMessage("Duplicate candidate evaluation recorded.");
      await loadAllData();
    } catch (err: any) {
      alert(err.message || "Failed to resolve duplicate");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevalidation = async () => {
    setActionLoading(true);
    try {
      await api.revalidateApplication(appId);
      setActionMessage("Selective revalidation finished. Affected checks evaluated.");
      await loadAllData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };


  const handleVerifyIssuer = async (docId: number) => {
    const doc = documents.find((d: any) => d.id === docId) || documents[0];
    if (doc) {
      handleOpenVerifyModal(doc);
    }
  };


  const handleCreateClarification = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionLoading(true);
    try {
      await api.createClarification(appId, {
        subject: clarSubject,
        requested_information: clarReqInfo,
        instructions_for_correction: clarInstructions,
        due_days: 7,
      });
      setShowClarificationModal(false);
      setClarSubject("");
      setClarReqInfo("");
      setClarInstructions("");
      await loadAllData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };


  const handleSubmitCorrection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!corrFile || !selectedClarificationId) {
      alert("Please choose a replacement file.");
      return;
    }
    setActionLoading(true);
    const fd = new FormData();
    fd.append("explanation", corrExplanation);
    fd.append("document_id", corrDocumentId.toString());
    fd.append("file", corrFile);

    try {
      await api.submitCorrection(selectedClarificationId, fd);
      setShowCorrectionModal(false);
      setCorrFile(null);
      setCorrExplanation("");
      await loadAllData();
      alert("Corrected document uploaded successfully. You can now revalidate the application.");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };


  const handleOpenDecisionModal = (initialType?: "APPROVE" | "REJECT" | "REQUEST_CORRECTION" | "REQUEST_DOCUMENTS" | "UNDER_REVIEW") => {
    if (initialType) {
      setDecisionType(initialType);
    }
    setConfirmStep(false);
    setShowDecisionModal(true);
  };

  const handleRecordDecision = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();

    const effectiveRejectionReason = rejectionReason === "Other Regulatory Disqualification"
      ? customRejectionReason.trim()
      : rejectionReason;

    // Validate based on decision type
    if (decisionType === "REJECT") {
      if (!effectiveRejectionReason) {
        alert("A rejection reason is strictly required when rejecting an application.");
        return;
      }
      if (!decisionJustification || decisionJustification.trim().length < 10) {
        alert("A detailed justification / explanation of at least 10 characters is required for rejection.");
        return;
      }
    } else if (decisionType === "APPROVE") {
      const activeCritical = findings.filter(f => f.is_active && f.status === "FAILED" && f.severity === "CRITICAL").length;
      if (activeCritical > 0 && !decisionOverride) {
        alert(`Cannot approve: application has ${activeCritical} unresolved critical finding(s). You must apply an authorized policy override.`);
        return;
      }
      if (decisionOverride && (!decisionOverrideReason || !decisionOverrideReason.trim())) {
        alert("Authorized policy override reason is mandatory when approving with active critical findings.");
        return;
      }
      if (!decisionJustification || !decisionJustification.trim()) {
        alert("Please provide an approval justification / memo.");
        return;
      }
    } else if (decisionType === "REQUEST_CORRECTION") {
      if (!decisionJustification || decisionJustification.trim().length < 5) {
        alert("Please provide detailed correction instructions for the institution.");
        return;
      }
    } else if (decisionType === "REQUEST_DOCUMENTS") {
      if (!decisionJustification || decisionJustification.trim().length < 5) {
        alert("Please specify which documents the institution must upload.");
        return;
      }
    }

    if (!confirmStep) {
      setConfirmStep(true);
      return;
    }

    setActionLoading(true);
    try {
      await api.recordDecision(appId, {
        decision: decisionType,
        justification: decisionJustification,
        rejection_reason: decisionType === "REJECT" ? effectiveRejectionReason : undefined,
        rule_ids: selectedFindingRuleIds.length > 0 ? selectedFindingRuleIds : undefined,
        document_ids: selectedAffectedDocIds.length > 0 ? selectedAffectedDocIds : undefined,
        is_override: decisionOverride,
        override_reason: decisionOverride ? decisionOverrideReason : undefined,
      });
      setShowDecisionModal(false);
      setConfirmStep(false);
      setDecisionJustification("");
      setDecisionOverride(false);
      setDecisionOverrideReason("");
      setSelectedFindingRuleIds([]);
      setSelectedAffectedDocIds([]);
      await loadAllData();
      setActionMessage(`Scrutiny action '${decisionType}' recorded successfully and institution users notified.`);
    } catch (err: any) {
      alert(err.message || "Failed to record scrutiny action");
    } finally {
      setActionLoading(false);
    }
  };


  const handleSaveCorrectionField = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedField) return;
    setActionLoading(true);
    try {
      await api.correctField(selectedField.id, {
        corrected_value: correctedValue,
        reason: correctionReason,
      });
      setShowCorrectFieldModal(false);
      await loadAllData();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };


  const handleUploadDocument = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      alert("Please select a document file to upload.");
      return;
    }
    setActionLoading(true);
    try {
      const fd = new FormData();
      fd.append("document_type", uploadDocType);
      fd.append("title", uploadDocTitle.trim() || uploadDocType.replace(/_/g, " "));
      fd.append("file", uploadFile);

      const res = await api.uploadDocument(appId, fd);
      setShowUploadModal(false);
      setUploadFile(null);
      setUploadDocTitle("");
      
      const vStatus = res?.latest_version?.status;
      if (vStatus === "FAILED") {
        setActionMessage(`Document uploaded with processing note: ${res?.latest_version?.error_message || "Text extraction unprocessable"}`);
      } else if (vStatus === "COMPLETED_WITH_WARNINGS") {
        setActionMessage("Document uploaded and recorded. Low text density observed; visual inspection recommended.");
      } else {
        setActionMessage("Document uploaded, cryptographically fingerprinted, and AI OCR structured fields extracted successfully!");
      }
      await loadAllData();
    } catch (err: any) {
      alert(err.message || "Failed to upload document");
    } finally {
      setActionLoading(false);
    }
  };


  if (!app && loading) {
    return (
      <div className="p-12 text-center text-slate-500 text-sm">
        Loading Application Scrutiny Workspace...
      </div>
    );
  }

  if (!app) {
    return (
      <div className="p-12 text-center text-rose-600 text-sm">
        Application not found.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Application Workspace Banner */}
      <div className="bg-white rounded-2xl p-6 border border-[#DCE4ED] shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-mono text-xs font-bold text-[#1677C8] bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                {app.reference_no}
              </span>
              <StatusBadge status={app.status} />
              {app.is_demo_seed && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-200">
                  SYNTHETIC DEMO SUBMISSION
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold text-slate-900">{app.title}</h1>
            <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-xs text-slate-600 mt-2">
              <div>
                <span className="font-semibold text-slate-700">Institution: </span>
                <span>{app.institution_name}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-700">Category: </span>
                <span>{app.category.replace(/_/g, " ")}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-700">Academic Year: </span>
                <span className="font-mono font-bold text-slate-800">{app.academic_year}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-700">Declared Intake: </span>
                <span>{app.declared_intake || "N/A"} seats</span>
              </div>
              <div>
                <span className="font-semibold text-slate-700">Declared Land: </span>
                <span>{app.declared_land_acres || "N/A"} Acres</span>
              </div>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {/* Run Validation Engine */}
            <button
              onClick={handleRunValidation}
              disabled={actionLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-[#1677C8] text-white hover:bg-[#1264a8] transition-colors shadow-xs cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${actionLoading ? "animate-spin" : ""}`} />
              <span>Run Validation</span>
            </button>

            {/* Revalidate (Change-Aware) */}
            <button
              onClick={handleRevalidation}
              disabled={actionLoading}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-700 text-white hover:bg-indigo-800 transition-colors shadow-xs cursor-pointer disabled:opacity-50"
              title="Runs selective revalidation on changed document versions"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Revalidate</span>
            </button>

            {/* Regulatory Scrutiny Actions (Officer) */}
            {isOfficerOrAdmin && (
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => handleOpenDecisionModal("APPROVE")}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold bg-emerald-700 hover:bg-emerald-800 text-white transition-colors shadow-xs cursor-pointer"
                  title="Approve application after scrutiny review"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Request Approval</span>
                </button>
                <button
                  onClick={() => handleOpenDecisionModal("REJECT")}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold bg-rose-700 hover:bg-rose-800 text-white transition-colors shadow-xs cursor-pointer"
                  title="Reject application with mandatory regulatory grounds"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  <span>Reject</span>
                </button>
                <button
                  onClick={() => handleOpenDecisionModal("REQUEST_CORRECTION")}
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold bg-[#0B2545] hover:bg-[#123B63] text-white transition-colors shadow-xs cursor-pointer"
                  title="All Scrutiny Decisions: Clarification, Missing Docs, or Under Review"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
                  <span>All Scrutiny Actions</span>
                </button>
              </div>
            )}

            {/* Download Report Buttons */}
            <button
              onClick={handleExportPdf}
              disabled={exportingPdf}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300 transition-colors disabled:opacity-50 cursor-pointer"
              title="Export complete regulatory scrutiny PDF report"
            >
              {exportingPdf ? (
                <div className="w-3.5 h-3.5 border-2 border-rose-600 border-t-transparent rounded-full animate-spin" />
              ) : (
                <FileDown className="w-3.5 h-3.5 text-rose-600" />
              )}
              <span>{exportingPdf ? "Generating PDF..." : "Export PDF"}</span>
            </button>
            <button
              onClick={handleExportCsv}
              disabled={exportingCsv}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300 transition-colors disabled:opacity-50 cursor-pointer"
              title="Export normalized compliance dataset as CSV"
            >
              {exportingCsv ? (
                <div className="w-3.5 h-3.5 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
              ) : (
                <Download className="w-3.5 h-3.5 text-emerald-600" />
              )}
              <span>{exportingCsv ? "Exporting CSV..." : "Export CSV"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Institution Notice Banners for Deficiencies & Clarifications */}
      {user?.role === "INSTITUTION_USER" && (
        <>
          {(app.status === "CLARIFICATION_REQUESTED" || app.status === "RETURNED") && (
            <div className="p-4 rounded-xl bg-amber-50 border-2 border-amber-300 text-amber-900 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-6 h-6 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-bold text-sm text-amber-900">
                    Action Required: Clarification & Document Rectification Requested
                  </h3>
                  <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                    AICTE Scrutiny Officers have reviewed your application and requested corrections or clarification. Please review the deficiency requirements and upload corrected evidence below. Historical document versions will remain intact in the immutable audit trail.
                  </p>
                  {clarifications.length > 0 && (
                    <div className="mt-2 text-xs font-semibold text-amber-950 bg-amber-100/70 p-2 rounded border border-amber-200">
                      Latest Request: "{clarifications[0].subject}" — {clarifications[0].instructions_for_correction || clarifications[0].requested_information}
                    </div>
                  )}
                </div>
              </div>
              <div className="shrink-0 flex items-center gap-2">
                <button
                  onClick={() => {
                    if (clarifications.length > 0) {
                      setSelectedClarificationId(clarifications[0].id);
                      if (clarifications[0].relevant_document_id) {
                        setCorrDocumentId(clarifications[0].relevant_document_id);
                      } else if (documents.length > 0) {
                        setCorrDocumentId(documents[0].id);
                      }
                      setShowCorrectionModal(true);
                    } else {
                      setActiveTab("clarifications");
                    }
                  }}
                  className="px-4 py-2 bg-amber-700 hover:bg-amber-800 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs cursor-pointer transition-colors"
                >
                  <Upload className="w-4 h-4" />
                  <span>Submit Rectified Document</span>
                </button>
              </div>
            </div>
          )}

          {app.status === "REJECTED" && (
            <div className="p-4 rounded-xl bg-rose-50 border-2 border-rose-300 text-rose-900 shadow-xs flex items-start gap-3">
              <XCircle className="w-6 h-6 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-bold text-sm text-rose-900">
                  Application Scrutiny Concluded: REJECTED
                </h3>
                <p className="text-xs text-rose-800 mt-1 leading-relaxed">
                  This application was rejected by AICTE Scrutiny Officers. Check the "Reviews & Audit" tab to inspect the formal rejection reason, cited compliance rules, and officer findings.
                </p>
              </div>
              <button
                onClick={() => setActiveTab("reviews")}
                className="px-3.5 py-1.5 bg-rose-700 hover:bg-rose-800 text-white rounded-lg text-xs font-bold shrink-0 cursor-pointer"
              >
                Inspect Rejection Reason
              </button>
            </div>
          )}

          {app.status === "CORRECTION_SUBMITTED" && (
            <div className="p-4 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-900 shadow-xs flex items-start gap-3">
              <CheckCircle2 className="w-6 h-6 text-indigo-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-bold text-sm text-indigo-900">
                  Correction Submitted — Under Officer Revalidation
                </h3>
                <p className="text-xs text-indigo-700 mt-1 leading-relaxed">
                  Your corrected evidence has been received and cryptographically fingerprinted. AICTE Scrutiny Officers have been notified and are re-evaluating compliance.
                </p>
              </div>
            </div>
          )}
        </>
      )}

      {/* Action Notification Banner */}
      {actionMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{actionMessage}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="text-emerald-700 hover:text-emerald-900 font-bold px-2 py-0.5"
          >
            ✕
          </button>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="flex border-b border-[#DCE4ED] bg-white rounded-t-xl px-4 pt-2 gap-1 overflow-x-auto text-xs font-bold">
        {[
          { key: "findings", label: `Validation Findings (${findings.length})`, icon: AlertTriangle },
          { key: "documents", label: `Document Intelligence (${documents.length})`, icon: FileCheck },
          { key: "anomalies", label: `Anomalies (${anomalies.length})`, icon: AlertCircle },
          { key: "verification", label: "Issuer Verification", icon: ShieldCheck },
          { key: "trustgraph", label: "TrustGraph Registry", icon: Network },
          { key: "clarifications", label: `Clarifications (${clarifications.length})`, icon: HelpCircle },
          { key: "reviews", label: `Reviews & Audit (${reviews.length})`, icon: History },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 px-4 py-2.5 border-b-2 font-semibold transition-colors whitespace-nowrap cursor-pointer ${
                isActive
                  ? "border-[#1677C8] text-[#1677C8] bg-blue-50/40 rounded-t-lg"
                  : "border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT 1: VALIDATION FINDINGS */}
      {activeTab === "findings" && (
        <div className="bg-white rounded-b-xl border border-[#DCE4ED] p-6 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#DCE4ED]">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Deterministic Compliance Findings</h2>
              <p className="text-xs text-slate-500">
                Evaluation results generated by the rules engine connected to actual extracted evidence
              </p>
            </div>
            <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
              <input
                type="checkbox"
                checked={includeHistoric}
                onChange={(e) => setIncludeHistoric(e.target.checked)}
                className="rounded border-slate-300 text-[#1677C8] focus:ring-[#1677C8]"
              />
              <span>Show Superseded Historic Findings</span>
            </label>
          </div>

          <div className="space-y-3">
            {findings.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                No active findings recorded. Click "Run Validation" to evaluate application against checklist rules.
              </div>
            ) : (
              findings.map((fnd) => (
                <div
                  key={fnd.id}
                  className={`p-4 rounded-xl border text-xs transition-all ${
                    fnd.status === "FAILED"
                      ? "border-rose-200 bg-rose-50/30"
                      : fnd.status === "WARNING"
                      ? "border-amber-200 bg-amber-50/30"
                      : fnd.status === "SUPERSEDED"
                      ? "border-slate-200 bg-slate-50 opacity-70"
                      : "border-emerald-200 bg-emerald-50/30"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-slate-800">{fnd.rule_code}</span>
                      <StatusBadge status={fnd.status} size="sm" />
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {fnd.severity}
                      </span>
                      {fnd.category && (
                        <span className="text-[10px] text-slate-500 font-medium">
                          ({fnd.category})
                        </span>
                      )}
                    </div>
                    {fnd.affected_claim_field && (
                      <span className="text-[10px] font-mono text-slate-500">
                        Field: {fnd.affected_claim_field}
                      </span>
                    )}
                  </div>

                  <div className="mt-2 text-slate-900 font-bold text-sm">
                    {fnd.rule_title}
                  </div>

                  <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2 p-2.5 rounded-lg bg-white/80 border border-slate-200 text-xs">
                    <div>
                      <span className="font-bold text-slate-600">Expected: </span>
                      <span className="text-slate-800">{fnd.expected_value || "Regulatory requirement"}</span>
                    </div>
                    <div>
                      <span className="font-bold text-slate-600">Observed: </span>
                      <span className={fnd.status === "FAILED" ? "text-rose-700 font-bold" : "text-slate-800"}>
                        {fnd.observed_value || "Extracted from document"}
                      </span>
                    </div>
                  </div>

                  <p className="mt-2 text-slate-700 leading-relaxed">
                    {fnd.explanation}
                  </p>

                  {fnd.recommended_action && (
                    <div className="mt-2.5 p-2 rounded bg-slate-100 border border-slate-200 text-[11px] text-slate-700 flex items-start gap-1.5">
                      <span className="font-bold text-[#1677C8] shrink-0">Next Action:</span>
                      <span>{fnd.recommended_action}</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT 2: DOCUMENT INTELLIGENCE & OCR */}
      {activeTab === "documents" && (
        <div className="bg-white rounded-b-xl border border-[#DCE4ED] p-6 space-y-6">
          <div className="flex items-center justify-between pb-2 border-b border-[#DCE4ED]">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Submitted Documents & OCR Extractions</h2>
              <p className="text-xs text-slate-500">
                Extracted metadata, cryptographic SHA-256 fingerprints, and manual verification controls
              </p>
            </div>
            {user?.role === "INSTITUTION_USER" && (
              <button
                onClick={() => setShowUploadModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#0B2545] text-white rounded-lg text-xs font-bold hover:bg-[#123B63]"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Upload Document</span>
              </button>
            )}
          </div>

          <div className="space-y-4">
            {documents.map((doc) => {
              const v = doc.latest_version;
              return (
                <div key={doc.id} className="p-4 rounded-xl border border-[#DCE4ED] bg-slate-50/50 text-xs">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#DCE4ED]">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900">{doc.title}</span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-bold">
                          {doc.document_type}
                        </span>
                        {v && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200 text-slate-800 font-bold">
                            v{v.version_number}
                          </span>
                        )}
                        {v && v.status === "COMPLETED" && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200">
                            PROCESSED
                          </span>
                        )}
                        {v && v.status === "COMPLETED_WITH_WARNINGS" && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">
                            PARTIAL OCR
                          </span>
                        )}
                        {v && v.status === "FAILED" && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-200">
                            OCR FAILED
                          </span>
                        )}
                      </div>
                      {v && (
                        <div className="text-[11px] text-slate-500 mt-1 flex flex-wrap gap-x-4">
                          <span>File: {v.original_filename || "Document File"}</span>
                          <span className="font-mono">Hash: {(v.file_hash || "").substring(0, 16)}...</span>
                          <span>Confidence: {v.ocr_confidence ? `${Math.round(v.ocr_confidence * 100)}%` : "N/A"}</span>
                        </div>
                      )}
                      {v && v.error_message && (
                        <div className="text-[11px] text-rose-700 bg-rose-50 border border-rose-200 p-2 rounded-lg mt-2 font-medium">
                          ⚠️ {v.error_message}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {v && (
                        <>
                          <button
                            onClick={() => handleOpenPreview(doc, v)}
                            className="px-2.5 py-1 text-xs font-semibold rounded bg-white text-slate-700 hover:bg-slate-100 border border-slate-300 flex items-center gap-1 cursor-pointer transition-colors"
                            title="Preview original uploaded file"
                          >
                            <Eye className="w-3.5 h-3.5 text-[#1677C8]" />
                            <span>View Doc</span>
                          </button>
                          <button
                            onClick={() => handleDownloadDirect(v)}
                            className="p-1 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 rounded border border-slate-300 transition-colors cursor-pointer"
                            title="Download original file"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => handleOpenVerifyModal(doc, v)}
                        className="px-2.5 py-1 text-xs font-bold rounded-lg bg-[#0B2545] hover:bg-[#123B63] text-white flex items-center gap-1.5 cursor-pointer shadow-xs transition-colors"
                        title="Inspect issuing authority & run official verification"
                      >
                        <ShieldCheck className="w-3.5 h-3.5 text-[#16A6C8]" />
                        <span>Verify Authority</span>
                      </button>
                    </div>
                  </div>

                  {/* Extracted Fields Table */}
                  <div className="mt-3">
                    <div className="text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-2">
                      OCR Extracted Field Entities
                    </div>
                    {v && v.extracted_fields && v.extracted_fields.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
                        {v.extracted_fields.map((field) => (
                          <div
                            key={field.id}
                            className="p-2.5 rounded-lg bg-white border border-slate-200 flex flex-col justify-between"
                          >
                            <div>
                              <div className="text-[10px] font-bold text-slate-500 uppercase">
                                {field.field_label}
                              </div>
                              <div className="font-semibold text-slate-900 mt-0.5">
                                {field.is_manually_corrected ? (
                                  <span className="text-[#1677C8]">
                                    {field.corrected_value}{" "}
                                    <span className="text-[9px] text-slate-400 line-through">
                                      ({field.extracted_value})
                                    </span>
                                  </span>
                                ) : (
                                  field.extracted_value
                                )}
                              </div>
                            </div>
                            <div className="mt-2 pt-1 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
                              <span>Page {field.source_page}</span>
                              {isOfficerOrAdmin && (
                                <button
                                  onClick={() => {
                                    setSelectedField(field);
                                    setCorrectedValue(field.extracted_value);
                                    setShowCorrectFieldModal(true);
                                  }}
                                  className="text-[#1677C8] hover:underline font-bold flex items-center gap-0.5 cursor-pointer"
                                >
                                  <Edit2 className="w-2.5 h-2.5" />
                                  <span>Correct</span>
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-slate-400 text-xs italic">
                        No structured fields extracted from this document yet.
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB CONTENT 3: ANOMALY & DUPLICATE DETECTION */}
      {activeTab === "anomalies" && (
        <div className="bg-white rounded-b-xl border border-[#DCE4ED] p-6 space-y-4">
          <div className="pb-2 border-b border-[#DCE4ED]">
            <h2 className="text-sm font-bold text-slate-900">Explainable Anomaly & Duplicate Detection</h2>
            <p className="text-xs text-slate-500">
              Deterministic screening for duplicate certificate collisions, exact file fingerprints, and contradictory dates
            </p>
          </div>

          {anomalies.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs bg-slate-50 rounded-xl border border-dashed border-slate-300">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              <div className="font-bold text-slate-800">No Anomalous Collisions Detected</div>
              <div className="text-slate-500 mt-0.5">
                All document hashes, certificate identifiers, and chronologies are uncompromised.
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {anomalies.map((anom, idx) => (
                <div key={idx} className="p-4 rounded-xl border border-rose-200 bg-rose-50/40 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-rose-900">{anom.anomaly_type}</span>
                    <span className="px-2 py-0.5 rounded bg-rose-200 text-rose-900 font-bold uppercase text-[10px]">
                      {anom.severity}
                    </span>
                  </div>
                  <p className="mt-1 text-slate-800 leading-relaxed font-medium">{anom.explanation}</p>
                  <div className="mt-2 text-[11px] text-slate-600 font-semibold">
                    Recommended Action: {anom.recommended_action}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT 4: ISSUER VERIFICATION */}
      {activeTab === "verification" && (
        <div className="bg-white rounded-b-xl border border-[#DCE4ED] p-6 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#DCE4ED]">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Issuing Authority Verification Registry</h2>
              <p className="text-xs text-slate-500">
                Direct lookup against state fire directorates, revenue land registries, and university academic portals
              </p>
            </div>
            <SimulatedBadge />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { code: "STATE_FIRE_SERVICES_PORTAL", docType: "FIRE_SAFETY_CERTIFICATE", title: "State Fire & Rescue Services", desc: "Fire Safety NOC verification adapter" },
              { code: "STATE_REVENUE_LAND_REGISTRY", docType: "LAND_DOCUMENT", title: "Revenue & Land Title Registry", desc: "Freehold ownership & encumbrance lookup" },
              { code: "AFFILIATING_UNIVERSITY_REGISTRY", docType: "AFFILIATION_CERTIFICATE", title: "University Academic Portal", desc: "Course-wise sanctioned intake validation" },
            ].map((src) => {
              const matchedDoc = documents.find((d: any) => d.document_type === src.docType || d.title.toLowerCase().includes(src.docType.toLowerCase().split("_")[0])) || documents[0];
              return (
                <div key={src.code} className="p-4 rounded-xl border border-[#DCE4ED] bg-slate-50 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                      <ShieldCheck className="w-4 h-4 text-[#1677C8]" />
                      <span>{src.title}</span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">{src.desc}</p>
                    {matchedDoc && (
                      <div className="mt-2 text-[11px] text-slate-600 bg-white p-2 rounded-lg border border-[#DCE4ED]">
                        <span className="font-semibold text-slate-500">Target Document: </span>
                        <span className="font-bold text-slate-800">{matchedDoc.title}</span>
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => matchedDoc && handleOpenVerifyModal(matchedDoc)}
                    disabled={actionLoading || !matchedDoc}
                    className="mt-4 w-full py-1.5 text-xs font-bold rounded-lg bg-[#0B2545] text-white hover:bg-[#123B63] transition-colors cursor-pointer flex items-center justify-center gap-1.5"
                  >
                    <ShieldCheck className="w-3.5 h-3.5 text-[#16A6C8]" />
                    <span>Verify Authority</span>
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB CONTENT 5: TRUSTGRAPH REGISTRY */}
      {activeTab === "trustgraph" && (
        <div className="space-y-4">
          <TrustGraphViewer data={trustGraph} loading={loading} />
        </div>
      )}

      {/* TAB CONTENT 6: CLARIFICATIONS & CORRECTIONS */}
      {activeTab === "clarifications" && (
        <div className="bg-white rounded-b-xl border border-[#DCE4ED] p-6 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-[#DCE4ED]">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Clarification Requests & Document Corrections</h2>
              <p className="text-xs text-slate-500">
                Interactive deficiency-resolution loop between AICTE Scrutiny Officers and Institutions
              </p>
            </div>
            {isOfficerOrAdmin && (
              <button
                onClick={() => setShowClarificationModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#0B2545] text-white rounded-lg text-xs font-bold hover:bg-[#123B63]"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                <span>New Clarification Request</span>
              </button>
            )}
          </div>

          <div className="space-y-4">
            {clarifications.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                No clarification requests have been issued for this application.
              </div>
            ) : (
              clarifications.map((clar) => (
                <div key={clar.id} className="p-4 rounded-xl border border-amber-200 bg-amber-50/20 text-xs space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-slate-900">{clar.subject}</span>
                        <StatusBadge status={clar.status} size="sm" />
                      </div>
                      <div className="text-[11px] text-slate-500 mt-0.5">
                        Issued by Officer: {clar.officer_name} | Created: {new Date(clar.created_at).toLocaleDateString()}
                      </div>
                    </div>

                    {user?.role === "INSTITUTION_USER" && clar.status === "OPEN" && (
                      <button
                        onClick={() => {
                          setSelectedClarificationId(clar.id);
                          setCorrDocumentId(documents[0]?.id || 1);
                          setShowCorrectionModal(true);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-[#1677C8] text-white font-bold hover:bg-[#1264a8] transition-colors cursor-pointer"
                      >
                        Submit Corrected Evidence
                      </button>
                    )}
                  </div>

                  <div className="p-3 rounded-lg bg-white border border-slate-200">
                    <span className="font-bold text-slate-700">Requested Information: </span>
                    <p className="text-slate-800 mt-1">{clar.requested_information}</p>
                    <span className="font-bold text-slate-700 mt-2 block">Instructions for Correction: </span>
                    <p className="text-slate-800 mt-0.5">{clar.instructions_for_correction}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT 7: REVIEWS & AUDIT */}
      {activeTab === "reviews" && (
        <div className="bg-white rounded-b-xl border border-[#DCE4ED] p-6 space-y-6">
          <div className="pb-2 border-b border-[#DCE4ED]">
            <h2 className="text-sm font-bold text-slate-900">Official Scrutiny Decisions, Reviews & Audit History</h2>
            <p className="text-xs text-slate-500">
              Immutable recorded actions, formal regulatory decisions, rejection reasons, and notes preserving governance.
            </p>
          </div>

          {/* Section 1: Formal Regulatory Decisions */}
          <div>
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">
              Official Workflow Decisions ({decisions.length})
            </h3>
            {decisions.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-400 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                No formal regulatory decisions recorded yet. Scrutiny is in preliminary progress.
              </div>
            ) : (
              <div className="space-y-3">
                {decisions.map((d) => (
                  <div
                    key={d.id}
                    className={`p-4 rounded-xl border text-xs ${
                      d.decision === "APPROVE"
                        ? "bg-emerald-50/50 border-emerald-200"
                        : d.decision === "REJECT"
                        ? "bg-rose-50/50 border-rose-200"
                        : d.decision === "REQUEST_CORRECTION" || d.decision === "RETURN"
                        ? "bg-amber-50/50 border-amber-200"
                        : "bg-blue-50/50 border-blue-200"
                    }`}
                  >
                    <div className="flex items-center justify-between pb-2 border-b border-slate-200/60">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                            d.decision === "APPROVE"
                              ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                              : d.decision === "REJECT"
                              ? "bg-rose-100 text-rose-800 border border-rose-300"
                              : d.decision === "REQUEST_CORRECTION" || d.decision === "RETURN"
                              ? "bg-amber-100 text-amber-800 border border-amber-300"
                              : "bg-sky-100 text-sky-800 border border-sky-300"
                          }`}
                        >
                          {d.decision.replace(/_/g, " ")}
                        </span>
                        <span className="font-bold text-slate-800">
                          Recorded by {d.officer_name}
                        </span>
                      </div>
                      <span className="font-mono text-[11px] text-slate-500">
                        {new Date(d.decided_at).toLocaleString()}
                      </span>
                    </div>

                    {d.rejection_reason && (
                      <div className="mt-2.5 p-2 rounded-lg bg-rose-100/70 border border-rose-300 text-rose-950 font-semibold">
                        <span className="text-[10px] uppercase font-bold text-rose-800 block mb-0.5">
                          Formal Rejection Grounds:
                        </span>
                        {d.rejection_reason}
                      </div>
                    )}

                    <div className="mt-2 text-slate-700 leading-relaxed font-sans">
                      <span className="font-bold text-slate-800">Justification: </span>
                      {d.justification}
                    </div>

                    {d.is_override && (
                      <div className="mt-2 text-[11px] text-amber-900 bg-amber-100/60 p-2 rounded border border-amber-200">
                        <span className="font-bold">Authorized Policy Override: </span>
                        {d.override_reason}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 2: Officer Scrutiny Notes */}
          <div>
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-3">
              Officer Review Notes ({reviews.length})
            </h3>
            {reviews.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-400 bg-slate-50 rounded-lg">
                No preliminary scrutiny notes recorded.
              </div>
            ) : (
              <div className="space-y-2">
                {reviews.map((r, i) => (
                  <div key={i} className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-xs">
                    <div className="flex items-center justify-between font-bold text-slate-800">
                      <span>{r.officer_name} ({r.review_stage})</span>
                      <span className="text-slate-400 font-mono text-[11px]">
                        {new Date(r.created_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="mt-1.5 text-slate-700 leading-relaxed">{r.review_notes}</p>
                    {r.recommended_action && (
                      <div className="mt-2 text-[10px] font-bold text-[#1677C8] uppercase">
                        Recommendation: {r.recommended_action}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 1: REQUEST CLARIFICATION */}
      {showClarificationModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-[#DCE4ED]">
            <h3 className="text-base font-bold text-slate-900 mb-1">Request Institutional Clarification</h3>
            <p className="text-xs text-slate-500 mb-4">
              Sends an official inquiry to the applicant requiring corrected evidence or justification
            </p>
            <form onSubmit={handleCreateClarification} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Subject</label>
                <input
                  type="text"
                  value={clarSubject}
                  onChange={(e) => setClarSubject(e.target.value)}
                  placeholder="e.g. Expired Fire NOC or Land Acreage Shortfall"
                  required
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="font-bold text-slate-700 block mb-1">Requested Information</label>
                <textarea
                  value={clarReqInfo}
                  onChange={(e) => setClarReqInfo(e.target.value)}
                  rows={3}
                  required
                  placeholder="Describe the discrepancy or missing requirement in detail..."
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="font-bold text-slate-700 block mb-1">Instructions for Correction</label>
                <textarea
                  value={clarInstructions}
                  onChange={(e) => setClarInstructions(e.target.value)}
                  rows={2}
                  required
                  placeholder="e.g. Upload renewed NOC Version 2 issued by competent authority..."
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowClarificationModal(false)}
                  className="px-4 py-2 border rounded-lg font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-[#0B2545] text-white rounded-lg font-bold hover:bg-[#123B63]"
                >
                  Send Clarification
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: SUBMIT CORRECTION */}
      {showCorrectionModal && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-[#DCE4ED]">
            <h3 className="text-base font-bold text-slate-900 mb-1">Submit Corrected Document (Version 2)</h3>
            <p className="text-xs text-slate-500 mb-4">
              Upload replacement document. Previous document versions will remain permanently in audit history.
            </p>
            <form onSubmit={handleSubmitCorrection} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Target Document Type</label>
                <select
                  value={corrDocumentId}
                  onChange={(e) => setCorrDocumentId(parseInt(e.target.value, 10))}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                >
                  {documents.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title} ({d.document_type})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="font-bold text-slate-700 block mb-1">Explanation of Correction</label>
                <textarea
                  value={corrExplanation}
                  onChange={(e) => setCorrExplanation(e.target.value)}
                  rows={2}
                  required
                  placeholder="Explain what was updated in this replacement version..."
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="font-bold text-slate-700 block mb-1">Select Replacement PDF File</label>
                <input
                  type="file"
                  accept=".pdf"
                  required
                  onChange={(e) => setCorrFile(e.target.files ? e.target.files[0] : null)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowCorrectionModal(false)}
                  className="px-4 py-2 border rounded-lg font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-[#1677C8] text-white rounded-lg font-bold hover:bg-[#1264a8]"
                >
                  Upload & Submit Version
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: FINAL DECISION & REQUEST APPROVAL */}
      {showDecisionModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-[#DCE4ED] max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Record Authorized Regulatory Decision
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Application: <span className="font-mono font-bold text-[#1677C8]">{app.reference_no}</span> • Institution: <span className="font-semibold text-slate-800">{app.institution_name}</span>
                </p>
              </div>
              <button
                onClick={() => {
                  setShowDecisionModal(false);
                  setConfirmStep(false);
                }}
                className="text-slate-400 hover:text-slate-700 text-sm font-bold p-1 rounded-md"
              >
                ✕
              </button>
            </div>

            {confirmStep ? (
              /* Confirmation Screen */
              <div className="py-4 space-y-4">
                <div className={`p-4 rounded-xl border ${
                  decisionType === "APPROVE" ? "bg-emerald-50 border-emerald-300 text-emerald-950" :
                  decisionType === "REJECT" ? "bg-rose-50 border-rose-300 text-rose-950" :
                  "bg-amber-50 border-amber-300 text-amber-950"
                }`}>
                  <div className="flex items-center gap-2 font-bold text-sm mb-1">
                    {decisionType === "APPROVE" && <CheckCircle2 className="w-5 h-5 text-emerald-600" />}
                    {decisionType === "REJECT" && <XCircle className="w-5 h-5 text-rose-600" />}
                    {decisionType !== "APPROVE" && decisionType !== "REJECT" && <AlertTriangle className="w-5 h-5 text-amber-600" />}
                    <span>Confirm Regulatory Action: {decisionType.replace(/_/g, " ")}</span>
                  </div>
                  <p className="text-xs leading-relaxed mt-2">
                    You are about to officially record this scrutiny decision for <span className="font-bold">{app.institution_name}</span> ({app.reference_no}). This action will be immutably recorded in the security audit ledger and will dispatch instant notifications strictly to authorized institutional representatives.
                  </p>
                  {decisionType === "REJECT" && (
                    <div className="mt-3 p-3 bg-white/80 rounded-lg border border-rose-200 text-xs">
                      <div className="font-bold text-rose-900 mb-0.5">Mandatory Rejection Grounds:</div>
                      <div className="font-semibold text-rose-800">
                        {rejectionReason === "Other Regulatory Disqualification" ? customRejectionReason : rejectionReason}
                      </div>
                      <div className="mt-2 text-slate-700">
                        <span className="font-bold">Officer Explanation:</span> {decisionJustification}
                      </div>
                    </div>
                  )}
                  {decisionType === "APPROVE" && decisionOverride && (
                    <div className="mt-3 p-3 bg-white/80 rounded-lg border border-amber-200 text-xs text-amber-900">
                      <span className="font-bold">Authorized Policy Override:</span> {decisionOverrideReason}
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t">
                  <button
                    type="button"
                    onClick={() => setConfirmStep(false)}
                    className="px-4 py-2 border border-slate-300 rounded-lg font-bold text-slate-700 hover:bg-slate-50 text-xs"
                  >
                    Back to Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRecordDecision()}
                    disabled={actionLoading}
                    className={`px-5 py-2 rounded-lg font-bold text-xs text-white shadow-md flex items-center gap-1.5 cursor-pointer ${
                      decisionType === "APPROVE" ? "bg-emerald-700 hover:bg-emerald-800" :
                      decisionType === "REJECT" ? "bg-rose-700 hover:bg-rose-800" :
                      "bg-[#0B2545] hover:bg-[#123B63]"
                    }`}
                  >
                    {actionLoading ? "Recording & Dispatching..." : `Confirm & Execute ${decisionType.replace(/_/g, " ")}`}
                  </button>
                </div>
              </div>
            ) : (
              /* Action Formulation Screen */
              <form onSubmit={(e) => { e.preventDefault(); handleRecordDecision(e); }} className="space-y-4 text-xs mt-3">
                {/* 5 Distinct Action Selector Tabs */}
                <div>
                  <label className="font-bold text-slate-700 block mb-1.5 uppercase text-[10px] tracking-wider">
                    Select Regulatory Action
                  </label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {[
                      { type: "APPROVE", label: "Approve Application", color: "hover:border-emerald-500", active: "bg-emerald-700 text-white border-emerald-700" },
                      { type: "REJECT", label: "Reject Application", color: "hover:border-rose-500", active: "bg-rose-700 text-white border-rose-700" },
                      { type: "REQUEST_CORRECTION", label: "Request Correction", color: "hover:border-amber-500", active: "bg-amber-600 text-white border-amber-600" },
                      { type: "REQUEST_DOCUMENTS", label: "Request Documents", color: "hover:border-purple-500", active: "bg-purple-700 text-white border-purple-700" },
                      { type: "UNDER_REVIEW", label: "Mark Under Review", color: "hover:border-sky-500", active: "bg-sky-700 text-white border-sky-700" },
                    ].map((act) => (
                      <button
                        key={act.type}
                        type="button"
                        onClick={() => setDecisionType(act.type as any)}
                        className={`p-2.5 rounded-lg border text-center font-bold transition-all cursor-pointer ${
                          decisionType === act.type
                            ? act.active
                            : `bg-slate-50 border-slate-200 text-slate-700 ${act.color}`
                        }`}
                      >
                        {act.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Specific Section: APPROVE */}
                {decisionType === "APPROVE" && (
                  <div className="space-y-3 p-3.5 bg-emerald-50/50 rounded-xl border border-emerald-200">
                    <div className="text-emerald-900 font-bold text-xs flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>Approval Scrutiny Clearance</span>
                    </div>

                    {/* Critical Failures Warning */}
                    {findings.filter(f => f.is_active && f.status === "FAILED" && f.severity === "CRITICAL").length > 0 && (
                      <div className="p-3 bg-amber-50 rounded-lg border border-amber-300 text-amber-900 text-xs">
                        <div className="font-bold flex items-center gap-1.5 text-amber-800">
                          <AlertTriangle className="w-4 h-4 text-amber-600" />
                          <span>Unresolved Critical Findings Detected ({findings.filter(f => f.is_active && f.status === "FAILED" && f.severity === "CRITICAL").length})</span>
                        </div>
                        <p className="mt-1 text-[11px] leading-relaxed">
                          AICTE regulatory standards require all critical non-compliances to be rectified. Approving this application requires an explicit, documented policy override.
                        </p>
                        <label className="flex items-center gap-2 font-bold text-amber-950 mt-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={decisionOverride}
                            onChange={(e) => setDecisionOverride(e.target.checked)}
                          />
                          <span>Authorize Regulatory Policy Override</span>
                        </label>
                        {decisionOverride && (
                          <input
                            type="text"
                            value={decisionOverrideReason}
                            onChange={(e) => setDecisionOverrideReason(e.target.value)}
                            placeholder="Specify mandatory policy override justification and executive authorization reference..."
                            className="w-full mt-2 p-2 border border-amber-300 rounded text-xs bg-white font-medium"
                            required={decisionOverride}
                          />
                        )}
                      </div>
                    )}

                    <div>
                      <label className="font-bold text-slate-700 block mb-1">
                        Approval Justification & Regulatory Clearance Basis <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        value={decisionJustification}
                        onChange={(e) => setDecisionJustification(e.target.value)}
                        rows={3}
                        required
                        placeholder="State clear regulatory grounds for approval (e.g. All statutory safety, infrastructure, and faculty norms satisfied)..."
                        className="w-full p-2.5 border border-slate-300 rounded-lg bg-white"
                      />
                    </div>
                  </div>
                )}

                {/* Specific Section: REJECT */}
                {decisionType === "REJECT" && (
                  <div className="space-y-3 p-3.5 bg-rose-50/50 rounded-xl border border-rose-200">
                    <div className="text-rose-900 font-bold text-xs flex items-center gap-1.5">
                      <XCircle className="w-4 h-4 text-rose-600" />
                      <span>Formal Regulatory Rejection Grounds (Mandatory)</span>
                    </div>

                    <div>
                      <label className="font-bold text-slate-800 block mb-1">
                        Rejection Reason Category <span className="text-rose-500">*</span>
                      </label>
                      <select
                        value={rejectionReason}
                        onChange={(e) => setRejectionReason(e.target.value)}
                        required
                        className="w-full p-2.5 border border-slate-300 rounded-lg bg-white font-semibold text-slate-900"
                      >
                        <option value="Critical Safety Compliance Shortfall (Expired / Invalid Fire NOC)">Critical Safety Compliance Shortfall (Expired / Invalid Fire NOC)</option>
                        <option value="Inadequate Land Title / Encumbrance / Ownership Defect">Inadequate Land Title / Encumbrance / Ownership Defect</option>
                        <option value="Lack of Mandatory University Affiliation Order">Lack of Mandatory University Affiliation Order</option>
                        <option value="Fraudulent or Cryptographically Tampered Document Submission">Fraudulent or Cryptographically Tampered Document Submission</option>
                        <option value="Deficient Built-Up Instructional Area / Space Norms Violation">Deficient Built-Up Instructional Area / Space Norms Violation</option>
                        <option value="Non-Compliance with Prescribed Faculty-to-Student Ratio">Non-Compliance with Prescribed Faculty-to-Student Ratio</option>
                        <option value="Failure to Submit Mandatory Audited Financial Statements">Failure to Submit Mandatory Audited Financial Statements</option>
                        <option value="Failure to Rectify Deficiencies within Prescribed Timeline">Failure to Rectify Deficiencies within Prescribed Timeline</option>
                        <option value="Other Regulatory Disqualification">Other Regulatory Disqualification (Specify below)</option>
                      </select>
                    </div>

                    {rejectionReason === "Other Regulatory Disqualification" && (
                      <div>
                        <label className="font-bold text-slate-800 block mb-1">
                          Specify Custom Rejection Grounds <span className="text-rose-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={customRejectionReason}
                          onChange={(e) => setCustomRejectionReason(e.target.value)}
                          placeholder="e.g. Non-accreditation by state statutory board"
                          required
                          className="w-full p-2 border border-slate-300 rounded-lg bg-white"
                        />
                      </div>
                    )}

                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="font-bold text-slate-800">
                          Detailed Rejection Explanation & Deficiencies <span className="text-rose-500">*</span>
                        </label>
                        <span className={`text-[10px] ${decisionJustification.length >= 10 ? 'text-emerald-600 font-bold' : 'text-slate-400'}`}>
                          {decisionJustification.length}/10 min chars
                        </span>
                      </div>
                      <textarea
                        value={decisionJustification}
                        onChange={(e) => setDecisionJustification(e.target.value)}
                        rows={3}
                        required
                        placeholder="Detail specific regulatory breaches, clauses violated, and evidence gaps supporting rejection..."
                        className="w-full p-2.5 border border-slate-300 rounded-lg bg-white"
                      />
                    </div>

                    {/* Checkbox list of active critical/failed findings */}
                    {findings.filter(f => f.is_active && f.status === "FAILED").length > 0 && (
                      <div>
                        <label className="font-bold text-slate-700 block mb-1 text-[11px]">
                          Select Supporting Validation Findings / Rule Violations:
                        </label>
                        <div className="max-h-28 overflow-y-auto border border-slate-200 rounded-lg p-2 bg-white space-y-1.5">
                          {findings.filter(f => f.is_active && f.status === "FAILED").map(f => (
                            <label key={f.id} className="flex items-start gap-2 cursor-pointer text-[11px] text-slate-700 hover:bg-slate-50 p-1 rounded">
                              <input
                                type="checkbox"
                                checked={selectedFindingRuleIds.includes(f.id)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedFindingRuleIds([...selectedFindingRuleIds, f.id]);
                                  } else {
                                    setSelectedFindingRuleIds(selectedFindingRuleIds.filter(id => id !== f.id));
                                  }
                                }}
                                className="mt-0.5"
                              />
                              <div>
                                <span className="font-bold text-rose-700">[{f.severity}]</span> {f.rule_code}: {f.rule_title}
                              </div>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Checkbox list of documents */}
                    {documents.length > 0 && (
                      <div>
                        <label className="font-bold text-slate-700 block mb-1 text-[11px]">
                          Select Affected Supporting Documents:
                        </label>
                        <div className="max-h-24 overflow-y-auto border border-slate-200 rounded-lg p-2 bg-white space-y-1">
                          {documents.map(d => (
                            <label key={d.id} className="flex items-center gap-2 cursor-pointer text-[11px] text-slate-700 hover:bg-slate-50 p-1 rounded">
                              <input
                                type="checkbox"
                                checked={selectedAffectedDocIds.includes(d.id)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedAffectedDocIds([...selectedAffectedDocIds, d.id]);
                                  } else {
                                    setSelectedAffectedDocIds(selectedAffectedDocIds.filter(id => id !== d.id));
                                  }
                                }}
                              />
                              <span className="font-medium">{d.title} ({d.document_type})</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Specific Section: REQUEST_CORRECTION */}
                {decisionType === "REQUEST_CORRECTION" && (
                  <div className="space-y-3 p-3.5 bg-amber-50/50 rounded-xl border border-amber-200">
                    <div className="text-amber-900 font-bold text-xs flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      <span>Return for Institutional Rectification</span>
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 block mb-1">
                        Detailed Rectification Instructions for Institution <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        value={decisionJustification}
                        onChange={(e) => setDecisionJustification(e.target.value)}
                        rows={3}
                        required
                        placeholder="Detail exactly what discrepancies must be resolved and what replacement evidence is required..."
                        className="w-full p-2.5 border border-slate-300 rounded-lg bg-white"
                      />
                    </div>
                  </div>
                )}

                {/* Specific Section: REQUEST_DOCUMENTS */}
                {decisionType === "REQUEST_DOCUMENTS" && (
                  <div className="space-y-3 p-3.5 bg-purple-50/50 rounded-xl border border-purple-200">
                    <div className="text-purple-900 font-bold text-xs flex items-center gap-1.5">
                      <FileText className="w-4 h-4 text-purple-600" />
                      <span>Request Missing / Additional Documents</span>
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 block mb-1">
                        Required Missing Documents & Instructions <span className="text-rose-500">*</span>
                      </label>
                      <textarea
                        value={decisionJustification}
                        onChange={(e) => setDecisionJustification(e.target.value)}
                        rows={3}
                        required
                        placeholder="List specific missing documents the applicant institution must upload..."
                        className="w-full p-2.5 border border-slate-300 rounded-lg bg-white"
                      />
                    </div>
                  </div>
                )}

                {/* Specific Section: UNDER_REVIEW */}
                {decisionType === "UNDER_REVIEW" && (
                  <div className="space-y-3 p-3.5 bg-sky-50/50 rounded-xl border border-sky-200">
                    <div className="text-sky-900 font-bold text-xs flex items-center gap-1.5">
                      <Info className="w-4 h-4 text-sky-600" />
                      <span>Scrutiny Progress Note</span>
                    </div>
                    <div>
                      <label className="font-bold text-slate-700 block mb-1">
                        Scrutiny Status Notes (Optional)
                      </label>
                      <textarea
                        value={decisionJustification}
                        onChange={(e) => setDecisionJustification(e.target.value)}
                        rows={2}
                        placeholder="e.g. Multi-disciplinary committee inspection in progress..."
                        className="w-full p-2.5 border border-slate-300 rounded-lg bg-white"
                      />
                    </div>
                  </div>
                )}

                <div className="flex justify-end gap-2 pt-3 border-t">
                  <button
                    type="button"
                    onClick={() => setShowDecisionModal(false)}
                    className="px-4 py-2 border border-slate-300 rounded-lg font-bold text-slate-600 hover:bg-slate-50 text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className={`px-5 py-2 rounded-lg font-bold text-xs text-white shadow-xs flex items-center gap-1.5 cursor-pointer ${
                      decisionType === "APPROVE" ? "bg-emerald-700 hover:bg-emerald-800" :
                      decisionType === "REJECT" ? "bg-rose-700 hover:bg-rose-800" :
                      decisionType === "REQUEST_CORRECTION" ? "bg-amber-600 hover:bg-amber-700" :
                      "bg-[#0B2545] hover:bg-[#123B63]"
                    }`}
                  >
                    <span>Proceed to Confirmation</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* MODAL 4: MANUAL FIELD CORRECTION */}
      {showCorrectFieldModal && selectedField && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-[#DCE4ED]">
            <h3 className="text-base font-bold text-slate-900 mb-1">Authorized OCR Field Correction</h3>
            <p className="text-xs text-slate-500 mb-4">
              Correct OCR misread value for <b>{selectedField.field_label}</b>. Original extraction preserved in audit log.
            </p>
            <form onSubmit={handleSaveCorrectionField} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Corrected Value</label>
                <input
                  type="text"
                  value={correctedValue}
                  onChange={(e) => setCorrectedValue(e.target.value)}
                  required
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="font-bold text-slate-700 block mb-1">Correction Reason</label>
                <input
                  type="text"
                  value={correctionReason}
                  onChange={(e) => setCorrectionReason(e.target.value)}
                  placeholder="e.g. Verified against page 2 seal"
                  required
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowCorrectFieldModal(false)}
                  className="px-4 py-2 border rounded-lg font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-[#1677C8] text-white rounded-lg font-bold hover:bg-[#1264a8]"
                >
                  Save Field Correction
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 5: UPLOAD REGULATORY DOCUMENT */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-[#DCE4ED] animate-in fade-in">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-xl bg-[#0B2545] text-white">
                  <Upload className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[#0B2545]">Upload Regulatory Document</h3>
                  <p className="text-xs text-slate-500">
                    Submit authentic institutional proof for AI OCR extraction & compliance validation
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-slate-600 font-bold p-1 text-sm rounded-lg hover:bg-slate-100"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUploadDocument} className="space-y-4 mt-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">
                  Document Type <span className="text-rose-500">*</span>
                </label>
                <select
                  value={uploadDocType}
                  onChange={(e) => setUploadDocType(e.target.value)}
                  required
                  className="w-full p-2.5 border border-slate-300 rounded-lg bg-white font-medium focus:ring-2 focus:ring-[#1677C8] focus:outline-none"
                >
                  <option value="FIRE_SAFETY_CERTIFICATE">Fire Safety Certificate / NOC</option>
                  <option value="LAND_DOCUMENTS">Land Title Deed / Ownership Records</option>
                  <option value="LAND_USE_CERTIFICATE">Land Use Certificate</option>
                  <option value="BUILDING_PLAN">Approved Building Plan / Completion Certificate</option>
                  <option value="OCCUPANCY_CERTIFICATE">Occupancy / Structural Stability Certificate</option>
                  <option value="AFFILIATION_ORDER">University Affiliation Order</option>
                  <option value="AUDITED_FINANCIALS">Audited Financial Statements</option>
                  <option value="FACULTY_LIST">Approved Faculty List</option>
                  <option value="OTHER">Other Supporting Regulatory Evidence</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">
                  Document Title <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={uploadDocTitle}
                  onChange={(e) => setUploadDocTitle(e.target.value)}
                  placeholder="e.g. State Fire Services NOC 2026-27"
                  required
                  className="w-full p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#1677C8] focus:outline-none font-medium"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">
                  Select Document File (PDF, PNG, JPG) <span className="text-rose-500">*</span>
                </label>
                <div className="border-2 border-dashed border-slate-300 rounded-xl p-4 text-center hover:border-[#1677C8] bg-slate-50/50 transition-colors">
                  <input
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    required
                    onChange={(e) => setUploadFile(e.target.files ? e.target.files[0] : null)}
                    className="w-full text-xs text-slate-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-bold file:bg-[#0B2545] file:text-white hover:file:bg-[#123B63] cursor-pointer"
                  />
                  <div className="text-[11px] text-slate-500 mt-2">
                    Max size: 15MB. Cryptographic SHA-256 fingerprint will be calculated upon upload.
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-blue-50 border border-blue-200 text-[11px] text-blue-900 leading-relaxed">
                <span className="font-bold">Automated Pipeline:</span> Uploaded files are immediately processed by PyMuPDF native OCR, extracted structured fields are verified against regulatory rules, and provenance nodes are added to TrustGraph.
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded-lg font-bold text-slate-600 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-4 py-2 bg-[#0B2545] text-white rounded-lg font-bold hover:bg-[#123B63] transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  {actionLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Processing OCR & Rules...</span>
                    </>
                  ) : (
                    <>
                      <Upload className="w-3.5 h-3.5" />
                      <span>Upload & Process Document</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Document Interactive Preview Modal */}
      <DocumentPreviewModal
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        document={previewDoc}
        version={previewVersion}
        applicationRef={app.reference_no}
      />

      {/* Authority Verification Modal */}
      <AuthorityVerificationModal
        isOpen={showVerifModal}
        onClose={() => setShowVerifModal(false)}
        document={verifDoc}
        version={verifVersion}
        isOfficerOrAdmin={isOfficerOrAdmin}
        onVerificationComplete={loadAllData}
      />
    </div>
  );
};

