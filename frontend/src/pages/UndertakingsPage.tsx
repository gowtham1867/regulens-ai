import React, { useState, useEffect } from "react";
import {
  FileCheck,
  Calendar,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Upload,
  HelpCircle,
  Search,
  Filter,
  ShieldCheck,
  ChevronRight
} from "lucide-react";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";
import { WhyExplanationModal } from "../components/common/WhyExplanationModal";

export const UndertakingsPage: React.FC = () => {
  const { user } = useAuth();
  const isOfficer = user?.role === "AICTE_OFFICER" || user?.role === "ADMINISTRATOR";
  const isInstitution = user?.role === "INSTITUTION_USER";

  const [undertakings, setUndertakings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Submit Evidence Modal
  const [evidenceModalOpen, setEvidenceModalOpen] = useState(false);
  const [selectedUt, setSelectedUt] = useState<any>(null);
  const [evidenceDescription, setEvidenceDescription] = useState("");
  const [submitLoading, setSubmitLoading] = useState(false);

  // Officer Review Modal
  const [reviewModalOpen, setReviewModalOpen] = useState(false);
  const [isCompliant, setIsCompliant] = useState(true);
  const [reviewNotes, setReviewNotes] = useState("");

  // Why Modal
  const [whyModalOpen, setWhyModalOpen] = useState(false);

  const fetchUndertakings = async () => {
    try {
      setLoading(true);
      const res = await api.get("/undertakings");
      setUndertakings(res.data);
    } catch (err) {
      console.error("Failed to load undertakings:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUndertakings();
  }, []);

  const openEvidenceModal = (ut: any) => {
    setSelectedUt(ut);
    setEvidenceDescription("");
    setEvidenceModalOpen(true);
  };

  const handleSubmitEvidence = async () => {
    if (!selectedUt || !evidenceDescription.trim()) return;
    try {
      setSubmitLoading(true);
      await api.post(`/undertakings/${selectedUt.id}/submit-evidence`, {
        evidence_description: evidenceDescription,
      });
      setEvidenceModalOpen(false);
      fetchUndertakings();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to submit evidence");
    } finally {
      setSubmitLoading(false);
    }
  };

  const openReviewModal = (ut: any) => {
    setSelectedUt(ut);
    setIsCompliant(true);
    setReviewNotes("");
    setReviewModalOpen(true);
  };

  const handleReviewCompliance = async () => {
    if (!selectedUt || !reviewNotes.trim()) return;
    try {
      setSubmitLoading(true);
      await api.post(`/undertakings/${selectedUt.id}/review`, {
        is_compliant: isCompliant,
        review_notes: reviewNotes,
      });
      setReviewModalOpen(false);
      fetchUndertakings();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to record compliance review");
    } finally {
      setSubmitLoading(false);
    }
  };

  const filtered = undertakings.filter((ut) => {
    if (search) {
      const q = search.toLowerCase();
      return (
        ut.undertaking_no.toLowerCase().includes(q) ||
        ut.condition_title.toLowerCase().includes(q) ||
        ut.institution_name.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-[#1677C8]/10 text-[#1677C8]">
              Phase 8 & 14
            </span>
            <span className="text-xs text-slate-500 font-medium">Post-Approval Compliance Tracking</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <FileCheck className="w-6 h-6 text-[#1677C8]" />
            Time-Bound Statutory Undertakings
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-3xl">
            Monitor and fulfill conditions attached to conditional approval letters (e.g. building completion, faculty cadre appointments).
          </p>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
          <div className="text-xs font-bold text-slate-700">
            Active Undertakings ({filtered.length})
          </div>
          <div className="relative w-72">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by ID, title, institute..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-300"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <th className="py-3 px-4">Undertaking No</th>
                <th className="py-3 px-4">Institution</th>
                <th className="py-3 px-4">Condition Title & Description</th>
                <th className="py-3 px-4">Statutory Due Date</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500 font-medium">
                    Loading statutory undertakings...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No statutory undertakings found.
                  </td>
                </tr>
              ) : (
                filtered.map((ut) => (
                  <tr key={ut.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-[#1677C8]">
                      {ut.undertaking_no}
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900">{ut.institution_name}</div>
                      <div className="text-[11px] text-slate-500 font-mono">{ut.application_reference}</div>
                    </td>
                    <td className="py-3 px-4 max-w-sm">
                      <div className="font-bold text-slate-900">{ut.condition_title}</div>
                      <div className="text-[11px] text-slate-600 line-clamp-2 mt-0.5">{ut.condition_description}</div>
                      <div className="text-[10px] text-[#1677C8] font-mono mt-1">{ut.aph_clause}</div>
                    </td>
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900">
                        {new Date(ut.due_date).toLocaleDateString()}
                      </div>
                      <div className={`text-[10px] font-bold ${ut.days_remaining < 0 ? 'text-rose-600' : 'text-slate-500'}`}>
                        {ut.days_remaining < 0 ? `Overdue by ${Math.abs(ut.days_remaining)}d` : `${ut.days_remaining}d remaining`}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {ut.status === "PENDING" && (
                        <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                          Pending Evidence
                        </span>
                      )}
                      {ut.status === "EVIDENCE_SUBMITTED" && (
                        <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 border border-blue-300">
                          Evidence Submitted
                        </span>
                      )}
                      {ut.status === "COMPLIANT" && (
                        <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                          Compliant (Verified)
                        </span>
                      )}
                      {ut.status === "DEFICIENT" && (
                        <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                          Deficient
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* Institution Action */}
                        {isInstitution && ut.status === "PENDING" && (
                          <button
                            onClick={() => openEvidenceModal(ut)}
                            className="px-2.5 py-1 bg-[#1677C8] hover:bg-[#123B63] text-white text-[11px] font-bold rounded-lg transition-colors flex items-center gap-1"
                          >
                            <Upload className="w-3 h-3" />
                            Submit Proof
                          </button>
                        )}

                        {/* Officer Review Action */}
                        {isOfficer && ut.status === "EVIDENCE_SUBMITTED" && (
                          <button
                            onClick={() => openReviewModal(ut)}
                            className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold rounded-lg transition-colors"
                          >
                            Verify Compliance
                          </button>
                        )}

                        <button
                          onClick={() => {
                            setSelectedUt(ut);
                            setWhyModalOpen(true);
                          }}
                          className="px-2 py-1 rounded bg-[#1677C8]/10 text-[#1677C8] text-[11px] font-bold hover:bg-[#1677C8]/20"
                        >
                          Why?
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Submit Evidence Modal */}
      {evidenceModalOpen && selectedUt && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">
              Submit Compliance Evidence
            </h3>
            <p className="text-xs text-slate-600">
              Provide photographic proof, architect completion certificate, or faculty appointment joining report for: {selectedUt.condition_title}.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Compliance Explanation & References:</label>
                <textarea
                  rows={4}
                  value={evidenceDescription}
                  onChange={(e) => setEvidenceDescription(e.target.value)}
                  placeholder="e.g. Completed 2nd floor laboratory wing with geo-tagged images. Architect certificate Ref # AC-2025-88 attached."
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setEvidenceModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitEvidence}
                disabled={submitLoading || !evidenceDescription.trim()}
                className="px-4 py-1.5 text-xs font-bold bg-[#1677C8] hover:bg-[#123B63] text-white rounded-lg disabled:opacity-50"
              >
                {submitLoading ? "Submitting..." : "Submit Compliance Proof"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Review Compliance Modal */}
      {reviewModalOpen && selectedUt && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">
              Verify Undertaking Compliance
            </h3>
            <p className="text-xs text-slate-600">
              Review submitted evidence for {selectedUt.condition_title}.
            </p>

            <div className="p-3 bg-slate-50 rounded-lg text-xs space-y-1">
              <span className="font-bold text-slate-700 block">Submitted Evidence:</span>
              <p className="text-slate-600">{selectedUt.evidence_description || "Architect certificate uploaded."}</p>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Compliance Determination:</label>
                <div className="flex items-center gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      checked={isCompliant}
                      onChange={() => setIsCompliant(true)}
                    />
                    <span className="text-emerald-700 font-bold">Compliant (Condition Satisfied)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      checked={!isCompliant}
                      onChange={() => setIsCompliant(false)}
                    />
                    <span className="text-rose-700 font-bold">Deficient (Rejected)</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Officer Scrutiny Notes:</label>
                <textarea
                  rows={3}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="e.g. Verified geo-tagged photographs and approved building completion letter."
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setReviewModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleReviewCompliance}
                disabled={submitLoading || !reviewNotes.trim()}
                className="px-4 py-1.5 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg disabled:opacity-50"
              >
                {submitLoading ? "Saving..." : "Record Verification Decision"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Why Modal */}
      {selectedUt && (
        <WhyExplanationModal
          isOpen={whyModalOpen}
          onClose={() => setWhyModalOpen(false)}
          entityType="obligation"
          entityId={selectedUt.application_id || 1}
        />
      )}
    </div>
  );
};
