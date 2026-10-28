import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  X,
  RefreshCw,
  ExternalLink,
  Building,
  Calendar,
  FileText,
  UserCheck,
  HelpCircle,
  FileCode,
  Info
} from "lucide-react";
import { api } from "../../services/api";

interface AuthorityVerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: any;
  version: any;
  isOfficerOrAdmin: boolean;
  onVerificationComplete: () => Promise<void>;
}

export const AuthorityVerificationModal: React.FC<AuthorityVerificationModalProps> = ({
  isOpen,
  onClose,
  document: doc,
  version: v,
  isOfficerOrAdmin,
  onVerificationComplete,
}) => {
  const [sources, setSources] = useState<any[]>([]);
  const [selectedSourceCode, setSelectedSourceCode] = useState<string>("AUTO");
  const [verifying, setVerifying] = useState(false);
  const [currentResult, setCurrentResult] = useState<any | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Manual Review Form
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualOutcome, setManualOutcome] = useState<string>("VERIFIED");
  const [manualNotes, setManualNotes] = useState<string>("");
  const [manualSubmitting, setManualSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen && doc) {
      loadSourcesAndHistory();
    } else {
      setCurrentResult(null);
      setError(null);
      setShowManualForm(false);
    }
  }, [isOpen, doc]);

  const loadSourcesAndHistory = async () => {
    try {
      setHistoryLoading(true);
      const [srcList, histList] = await Promise.all([
        api.getVerificationSources().catch(() => []),
        api.getVerificationHistory(doc.id).catch(() => []),
      ]);
      setSources(srcList);
      setHistory(histList);
      if (histList.length > 0) {
        setCurrentResult(histList[0]);
      }
    } catch (err: any) {
      console.error("Failed to load verification metadata:", err);
    } finally {
      setHistoryLoading(false);
    }
  };

  if (!isOpen || !doc) return null;

  // Extract relevant field values from version
  const fields = v?.extracted_fields || [];
  const certNumberField = fields.find((f: any) =>
    ["certificate_number", "noc_number", "patta_number", "deed_number"].includes(f.field_key)
  );
  const certNumber = certNumberField?.corrected_value || certNumberField?.extracted_value || "Pending Extraction";

  const issueDateField = fields.find((f: any) => f.field_key.includes("issue"));
  const issueDate = issueDateField?.corrected_value || issueDateField?.extracted_value || "N/A";

  const expiryDateField = fields.find((f: any) => f.field_key.includes("expiry") || f.field_key.includes("valid"));
  const expiryDate = expiryDateField?.corrected_value || expiryDateField?.extracted_value || "N/A";

  const issuerField = fields.find((f: any) => f.field_key.includes("authority") || f.field_key.includes("issuer"));
  const issuerName = issuerField?.corrected_value || issuerField?.extracted_value || "Recognized Competent Authority";

  // Automated Verification Trigger
  const handleRunVerification = async (force: boolean = false) => {
    setVerifying(true);
    setError(null);
    try {
      const sourceToUse = selectedSourceCode === "AUTO" ? undefined : selectedSourceCode;
      const res = await api.verifyDocument(doc.id, sourceToUse, force);
      setCurrentResult(res);
      await loadSourcesAndHistory();
      await onVerificationComplete();
    } catch (err: any) {
      setError(err.message || "Failed to execute authority verification check.");
    } finally {
      setVerifying(false);
    }
  };

  // Manual Officer Verification Submission
  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualNotes.trim()) {
      setError("Please provide official verification inspection notes.");
      return;
    }
    setManualSubmitting(true);
    setError(null);
    try {
      const res = await api.manualVerifyDocument(doc.id, {
        outcome: manualOutcome,
        notes: manualNotes,
        issuing_authority: issuerName,
        certificate_number: certNumber,
      });
      setCurrentResult(res);
      setShowManualForm(false);
      setManualNotes("");
      await loadSourcesAndHistory();
      await onVerificationComplete();
    } catch (err: any) {
      setError(err.message || "Manual verification submission failed.");
    } finally {
      setManualSubmitting(false);
    }
  };

  const renderOutcomeBadge = (outcome: string) => {
    switch (outcome) {
      case "VERIFIED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Verified Authenticity</span>
          </span>
        );
      case "MISMATCH_DETECTED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-50 text-rose-800 border border-rose-200">
            <XCircle className="w-4 h-4 text-rose-600" />
            <span>Failed Verification (Mismatch Detected)</span>
          </span>
        );
      case "SOURCE_UNAVAILABLE":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-orange-50 text-orange-800 border border-orange-200">
            <Clock className="w-4 h-4 text-orange-600" />
            <span>Verification Unavailable (Registry Timeout)</span>
          </span>
        );
      case "MANUAL_REVIEW_REQUIRED":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Manual Review Required</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200">
            <HelpCircle className="w-4 h-4 text-slate-500" />
            <span>Pending Verification</span>
          </span>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-[#DCE4ED] w-full max-w-3xl overflow-hidden flex flex-col max-h-[92vh] animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="p-5 bg-[#0B2545] text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#1677C8] flex items-center justify-center text-white shadow-sm">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight">
                Issuing Authority Verification Inspector
              </h2>
              <p className="text-xs text-slate-300">
                Official registry validation & provenance authentication for AICTE scrutiny
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1 text-xs">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 flex items-start gap-2.5">
              <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Section 1: Document Evidence Card */}
          <div className="p-4 rounded-xl border border-[#DCE4ED] bg-slate-50 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-[#DCE4ED]">
              <div className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#1677C8]" />
                <span>{doc.title}</span>
                <span className="text-[11px] font-semibold text-slate-500 font-mono">
                  (Version {v?.version_number || 1})
                </span>
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider bg-white px-2 py-0.5 rounded border border-[#DCE4ED] text-slate-700">
                {doc.document_type}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-slate-700">
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-400">Certificate / Ref No.</div>
                <div className="font-mono font-bold text-slate-900 mt-0.5 truncate" title={certNumber}>
                  {certNumber}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-400">Issuing Authority</div>
                <div className="font-semibold text-slate-900 mt-0.5 truncate" title={issuerName}>
                  {issuerName}
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-400">Issue Date</div>
                <div className="font-mono text-slate-800 mt-0.5">{issueDate}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-400">Valid Upto</div>
                <div className="font-mono text-slate-800 mt-0.5">{expiryDate}</div>
              </div>
            </div>
          </div>

          {/* Section 2: Automated Registry Verification Action */}
          <div className="p-4 rounded-xl border border-blue-100 bg-blue-50/50 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-[#0B2545] text-xs">Official Verification Registry</h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Direct inquiry against state fire directorates, land records, or affiliating universities
                </p>
              </div>
              {currentResult && renderOutcomeBadge(currentResult.outcome)}
            </div>

            <div className="flex flex-col sm:flex-row items-center gap-2.5 pt-1">
              <select
                value={selectedSourceCode}
                onChange={(e) => setSelectedSourceCode(e.target.value)}
                className="w-full sm:w-auto flex-1 bg-white border border-[#DCE4ED] rounded-xl px-3 py-2 text-xs font-medium text-slate-900 focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
              >
                <option value="AUTO">Auto-Match Registry by Document Type</option>
                {sources.map((s) => (
                  <option key={s.source_code} value={s.source_code}>
                    {s.name} ({s.verification_method})
                  </option>
                ))}
              </select>

              <button
                onClick={() => handleRunVerification(true)}
                disabled={verifying}
                className="w-full sm:w-auto px-4 py-2 rounded-xl bg-[#0B2545] hover:bg-[#123B63] text-white font-bold text-xs shadow-xs transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 shrink-0"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${verifying ? "animate-spin" : ""}`} />
                <span>{verifying ? "Executing Authority Query..." : "Verify Authority"}</span>
              </button>
            </div>

            {/* Explanation Notice */}
            <div className="flex items-start gap-2 text-[11px] text-slate-500 bg-white/80 p-2.5 rounded-lg border border-blue-100">
              <Info className="w-3.5 h-3.5 text-[#1677C8] shrink-0 mt-0.5" />
              <span>
                <b>Note:</b> OCR extraction alone does not confer authenticity. A successful outcome confirms that official authority records corroborate the certificate details. Registry connection timeouts are flagged as <i>Verification Unavailable</i> without assuming document falsification.
              </span>
            </div>
          </div>

          {/* Section 3: Active Result Details (if any) */}
          {currentResult && (
            <div className="p-4 rounded-xl border border-[#DCE4ED] bg-white space-y-2">
              <div className="flex items-center justify-between font-bold text-slate-800 text-xs">
                <span>Verification Outcome Details</span>
                <span className="text-[11px] font-normal text-slate-400 font-mono">
                  {new Date(currentResult.response_timestamp || currentResult.request_timestamp).toLocaleString()}
                </span>
              </div>

              {currentResult.failure_reason && (
                <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <span>{currentResult.failure_reason}</span>
                </div>
              )}

              {currentResult.evidence_payload && (
                <div className="space-y-1">
                  <div className="text-[10px] uppercase font-bold text-slate-400">
                    Registry Response Evidence Payload
                  </div>
                  <pre className="p-3 rounded-lg bg-slate-900 text-emerald-400 font-mono text-[11px] overflow-x-auto max-h-36">
                    {(() => {
                      try {
                        return JSON.stringify(JSON.parse(currentResult.evidence_payload), null, 2);
                      } catch {
                        return currentResult.evidence_payload;
                      }
                    })()}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Section 4: Manual Officer Review (For AICTE Officers) */}
          {isOfficerOrAdmin && (
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/60 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-900 text-xs">AICTE Officer Manual Attestation</h3>
                  <p className="text-[11px] text-slate-500">
                    Required when automated registries are unavailable or when conducting physical seal review
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowManualForm(!showManualForm)}
                  className="px-3 py-1 text-xs font-bold text-[#1677C8] hover:text-[#0B2545] border border-blue-200 rounded-lg bg-white transition-colors cursor-pointer"
                >
                  {showManualForm ? "Cancel Manual Review" : "+ Record Manual Attestation"}
                </button>
              </div>

              {showManualForm && (
                <form onSubmit={handleManualSubmit} className="space-y-3 pt-2">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      Verification Determination <span className="text-rose-500">*</span>
                    </label>
                    <select
                      value={manualOutcome}
                      onChange={(e) => setManualOutcome(e.target.value)}
                      className="w-full bg-white border border-[#DCE4ED] rounded-xl px-3 py-1.5 text-xs font-semibold"
                    >
                      <option value="VERIFIED">Verified — Physical Seal & Issuing Office Corroborated</option>
                      <option value="MISMATCH_DETECTED">Failed Verification — Document Altered or Mismatched</option>
                      <option value="MANUAL_REVIEW_REQUIRED">Manual Review Pending — Further Inquiries In-Progress</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      Official Inspection Notes & Evidence Reference <span className="text-rose-500">*</span>
                    </label>
                    <textarea
                      rows={2}
                      value={manualNotes}
                      onChange={(e) => setManualNotes(e.target.value)}
                      placeholder="e.g. Inspected official wet-ink seal and registrar signature. Confirmed dispatch register entry with District Fire Officer."
                      required
                      className="w-full p-2.5 bg-white border border-[#DCE4ED] rounded-xl text-xs focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
                    />
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={manualSubmitting}
                      className="px-4 py-2 rounded-xl bg-[#0B2545] hover:bg-[#123B63] text-white font-bold text-xs shadow-xs transition-colors flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      <span>{manualSubmitting ? "Persisting Officer Review..." : "Record Official Attestation"}</span>
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* Section 5: Verification History Log */}
          <div className="space-y-2 pt-1">
            <h4 className="font-bold text-slate-800 text-xs">
              Persisted Verification Audit Trail ({history.length} records)
            </h4>

            {historyLoading ? (
              <div className="p-4 text-center text-slate-400">Loading audit history...</div>
            ) : history.length === 0 ? (
              <div className="p-3 rounded-lg border border-dashed border-[#DCE4ED] text-slate-400 text-center text-xs">
                No previous verification attempts recorded for this document version.
              </div>
            ) : (
              <div className="divide-y divide-slate-100 border border-[#DCE4ED] rounded-xl overflow-hidden max-h-48 overflow-y-auto">
                {history.map((att) => (
                  <div key={att.id} className="p-2.5 flex items-center justify-between bg-white hover:bg-slate-50 transition-colors">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-800">{att.source_name}</span>
                        <span className="text-[10px] text-slate-400 font-mono">({att.verification_method})</span>
                        {att.is_reused && (
                          <span className="text-[9px] bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded">Reused Cache</span>
                        )}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        Ref: {att.certificate_number || "N/A"} • {new Date(att.response_timestamp || att.request_timestamp).toLocaleString()}
                      </div>
                    </div>
                    {renderOutcomeBadge(att.outcome)}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 border-t border-[#DCE4ED] flex items-center justify-between">
          <div className="text-[11px] text-slate-500">
            Cryptographic audit event automatically logged upon execution
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-white border border-[#DCE4ED] text-slate-700 font-bold text-xs hover:bg-slate-100 transition-colors cursor-pointer"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};

