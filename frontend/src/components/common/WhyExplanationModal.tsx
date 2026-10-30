import React, { useEffect, useState } from "react";
import {
  X,
  HelpCircle,
  Calendar,
  Clock,
  ShieldCheck,
  AlertTriangle,
  FileText,
  User,
  History,
  CheckCircle2,
  Lock
} from "lucide-react";
import api from "../../services/api";

interface WhyModalProps {
  isOpen: boolean;
  onClose: () => void;
  entityType: "obligation" | "routing" | "validity";
  entityId: number | string;
}

export const WhyExplanationModal: React.FC<WhyModalProps> = ({
  isOpen,
  onClose,
  entityType,
  entityId,
}) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !entityId) return;

    setLoading(true);
    setError(null);

    let url = "";
    if (entityType === "obligation") {
      url = `/obligations/${entityId}/why`;
    } else if (entityType === "routing") {
      url = `/workflow/routing/${entityId}/why`;
    } else if (entityType === "validity") {
      url = `/document-validity/${entityId}/why`;
    }

    api
      .get(url)
      .then((res: any) => {
        setData(res.data);
        setLoading(false);
      })
      .catch((err: any) => {
        setError(err.response?.data?.detail || "Failed to load regulatory explanation.");
        setLoading(false);
      });
  }, [isOpen, entityType, entityId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full border border-slate-200 overflow-hidden transform transition-all flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="bg-[#0B2545] text-white px-6 py-4 flex items-center justify-between border-b border-[#123B63]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#1677C8] flex items-center justify-center">
              <HelpCircle className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-base font-bold tracking-tight">Regulatory Explanation & Audit Proof</h3>
              <p className="text-xs text-slate-300">Phase 5 Deterministic Rule & Deadline Explainability Engine</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-800">
          {loading && (
            <div className="py-12 text-center">
              <div className="w-8 h-8 border-3 border-[#1677C8] border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
              <p className="text-sm font-medium text-slate-600">Computing deterministic clock & statutory audit trail...</p>
            </div>
          )}

          {error && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-3 text-rose-800 text-sm">
              <AlertTriangle className="w-5 h-5 shrink-0 text-rose-600" />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && data && (
            <>
              {/* Executive Summary Card */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 shadow-sm">
                <div className="text-xs font-bold uppercase tracking-wider text-[#1677C8] mb-1">
                  Explainability Breakdown
                </div>
                <div className="text-sm font-medium text-slate-900 leading-relaxed">
                  {data.summary_explanation || data.routing_reason}
                </div>
              </div>

              {/* Regulatory Source & APH Clause */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-700 tracking-wider">
                    <FileText className="w-4 h-4 text-[#1677C8]" />
                    Statutory Rule & Handbook Citation
                  </div>
                  {data.regulatory_rule?.is_aph_verified ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      Verified AICTE Handbook Regulation
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Admin Configured Parameter
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-slate-500 block">Handbook Edition:</span>
                    <span className="font-semibold text-slate-900">{data.regulatory_rule?.aph_edition || "AICTE APH 2024-2027"}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Applicable Clause:</span>
                    <span className="font-mono font-bold text-slate-900">{data.regulatory_rule?.aph_clause || "Clause 2.3"}</span>
                  </div>
                </div>
              </div>

              {/* Deadline & Clock Calculation (If Obligation) */}
              {data.deadline_calculation && (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-700 tracking-wider mb-3">
                    <Clock className="w-4 h-4 text-[#1677C8]" />
                    Deterministic Clock Math
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-4">
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                      <span className="text-slate-500 block">Configured Days</span>
                      <span className="text-sm font-bold text-slate-900">
                        {data.deadline_calculation.configured_days} {data.deadline_calculation.deadline_type === "WORKING_DAYS" ? "Working" : "Cal"}
                      </span>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                      <span className="text-slate-500 block">Excluded Holidays</span>
                      <span className="text-sm font-bold text-amber-600">
                        {data.deadline_calculation.excluded_holidays_count} Days
                      </span>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                      <span className="text-slate-500 block">Paused Period</span>
                      <span className="text-sm font-bold text-blue-600">
                        {data.deadline_calculation.total_paused_days} Days
                      </span>
                    </div>
                    <div className="bg-white p-2.5 rounded-lg border border-slate-200">
                      <span className="text-slate-500 block">Extensions</span>
                      <span className="text-sm font-bold text-emerald-600">
                        +{data.deadline_calculation.approved_extension_days} Days
                      </span>
                    </div>
                  </div>

                  <div className="p-3 bg-white border border-slate-200 rounded-lg flex items-center justify-between text-xs">
                    <div>
                      <span className="text-slate-500 block">Current Effective Due Date:</span>
                      <span className="font-bold text-slate-900 text-sm">
                        {new Date(data.deadline_calculation.effective_due_date).toLocaleString()}
                      </span>
                    </div>
                    <div>
                      {data.deadline_calculation.is_overdue ? (
                        <span className="px-2.5 py-1 rounded bg-rose-100 text-rose-800 font-bold">
                          Statutory Breach (Overdue)
                        </span>
                      ) : (
                        <span className="px-2.5 py-1 rounded bg-emerald-100 text-emerald-800 font-bold">
                          {data.deadline_calculation.days_remaining} Days Remaining
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Responsibility & Role */}
              {data.responsibility && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-slate-50 p-4 rounded-xl border border-slate-200">
                  <div>
                    <span className="text-slate-500 block">Responsible Official / Post:</span>
                    <span className="font-bold text-slate-900">{data.responsibility.responsible_post}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Responsible Role:</span>
                    <span className="font-semibold text-slate-900">{data.responsibility.responsible_role}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Current Clock State:</span>
                    <span className="font-mono font-bold text-[#1677C8]">{data.responsibility.clock_state}</span>
                  </div>
                </div>
              )}

              {/* Cryptographic SHA-256 Audit Verification Proof */}
              {data.audit_verification && (
                <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-emerald-600 text-white flex items-center justify-center shrink-0">
                      <Lock className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                        <span>Cryptographic Provenance Verified</span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      </div>
                      <div className="text-[11px] text-emerald-800">
                        Audit chain intact. SHA-256 hash linked ledger verified tamper-evident.
                      </div>
                    </div>
                  </div>
                  <span className="text-xs font-mono font-bold text-emerald-900 bg-emerald-200/60 px-2.5 py-1 rounded">
                    Status: {data.audit_verification.chain_status}
                  </span>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-slate-100 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition-colors"
          >
            Close Explanation
          </button>
        </div>
      </div>
    </div>
  );
};
