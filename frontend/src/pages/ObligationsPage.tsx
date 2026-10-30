import React, { useState, useEffect } from "react";
import {
  Clock,
  AlertTriangle,
  CheckCircle2,
  PauseCircle,
  PlayCircle,
  Plus,
  HelpCircle,
  Calendar,
  Filter,
  Search,
  ArrowRight,
  ShieldAlert,
  Layers,
  ChevronRight
} from "lucide-react";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";
import { WhyExplanationModal } from "../components/common/WhyExplanationModal";

export const ObligationsPage: React.FC = () => {
  const { user } = useAuth();
  const isOfficer = user?.role === "AICTE_OFFICER" || user?.role === "ADMINISTRATOR";

  const [obligations, setObligations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("ALL");
  const [search, setSearch] = useState("");

  // Modal states
  const [whyModalOpen, setWhyModalOpen] = useState(false);
  const [selectedObligationId, setSelectedObligationId] = useState<number | null>(null);

  // Action Modals
  const [pauseModalOpen, setPauseModalOpen] = useState(false);
  const [extensionModalOpen, setExtensionModalOpen] = useState(false);
  const [actionReason, setActionReason] = useState("");
  const [extensionDays, setExtensionDays] = useState(7);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchObligations = async () => {
    try {
      setLoading(true);
      const res = await api.get("/obligations");
      setObligations(res.data);
    } catch (err) {
      console.error("Failed to load obligations:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchObligations();
  }, []);

  const openWhyModal = (id: number) => {
    setSelectedObligationId(id);
    setWhyModalOpen(true);
  };

  const handlePauseClock = async () => {
    if (!selectedObligationId || !actionReason) return;
    try {
      setActionLoading(true);
      await api.post(`/obligations/${selectedObligationId}/pause`, {
        reason: actionReason,
        pause_state: "PAUSED_INSTITUTION",
      });
      setPauseModalOpen(false);
      setActionReason("");
      fetchObligations();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to pause clock");
    } finally {
      setActionLoading(false);
    }
  };

  const handleResumeClock = async (id: number) => {
    const reason = prompt("Enter resumption note (e.g. Institution submitted clarification response):");
    if (!reason) return;
    try {
      await api.post(`/obligations/${id}/resume`, { reason });
      fetchObligations();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to resume clock");
    }
  };

  const handleGrantExtension = async () => {
    if (!selectedObligationId || !actionReason) return;
    try {
      setActionLoading(true);
      await api.post(`/obligations/${selectedObligationId}/extension`, {
        additional_days: extensionDays,
        reason: actionReason,
      });
      setExtensionModalOpen(false);
      setActionReason("");
      fetchObligations();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to grant extension");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCompleteObligation = async (id: number) => {
    const reason = prompt("Enter completion / verification justification:");
    if (!reason) return;
    try {
      await api.post(`/obligations/${id}/complete`, { reason });
      fetchObligations();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to complete obligation");
    }
  };

  // Filter logic
  const filtered = obligations.filter((obl) => {
    if (activeTab === "RUNNING" && (obl.status !== "RUNNING" || obl.clock_state !== "RUNNING")) return false;
    if (activeTab === "PAUSED" && !obl.clock_state?.startsWith("PAUSED")) return false;
    if (activeTab === "OVERDUE" && obl.status !== "OVERDUE" && obl.status !== "BREACHED") return false;
    if (activeTab === "MET" && obl.status !== "MET") return false;

    if (search) {
      const q = search.toLowerCase();
      return (
        obl.obligation_no.toLowerCase().includes(q) ||
        obl.title.toLowerCase().includes(q) ||
        obl.institution_name.toLowerCase().includes(q) ||
        obl.responsible_post.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const totalCount = obligations.length;
  const runningCount = obligations.filter((o) => o.status === "RUNNING" && o.clock_state === "RUNNING").length;
  const pausedCount = obligations.filter((o) => o.clock_state?.startsWith("PAUSED")).length;
  const overdueCount = obligations.filter((o) => o.status === "OVERDUE" || o.status === "BREACHED").length;
  const metCount = obligations.filter((o) => o.status === "MET").length;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-[#1677C8]/10 text-[#1677C8]">
              Phase 2 & Phase 4
            </span>
            <span className="text-xs text-slate-500 font-medium">SIH PS 26262 Core Foundation</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <Layers className="w-6 h-6 text-[#1677C8]" />
            Central Promise Ledger & Regulatory Clocks
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-3xl">
            Immutable tracking ledger for every statutory obligation, deadline, paused interval, and escalation level.
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div
          onClick={() => setActiveTab("ALL")}
          className={`cursor-pointer bg-white p-4 rounded-xl border transition-all ${
            activeTab === "ALL" ? "border-[#1677C8] ring-2 ring-[#1677C8]/20 shadow" : "border-slate-200 hover:border-slate-300"
          }`}
        >
          <div className="text-xs font-semibold text-slate-500">Total Obligations</div>
          <div className="text-2xl font-black text-slate-900 mt-1">{totalCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Across all institutions</div>
        </div>

        <div
          onClick={() => setActiveTab("RUNNING")}
          className={`cursor-pointer bg-white p-4 rounded-xl border transition-all ${
            activeTab === "RUNNING" ? "border-emerald-500 ring-2 ring-emerald-500/20 shadow" : "border-slate-200 hover:border-slate-300"
          }`}
        >
          <div className="text-xs font-semibold text-emerald-700 flex items-center justify-between">
            <span>Running Clocks</span>
            <PlayCircle className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-black text-emerald-800 mt-1">{runningCount}</div>
          <div className="text-[11px] text-emerald-600 mt-1">Active scrutiny clocks</div>
        </div>

        <div
          onClick={() => setActiveTab("PAUSED")}
          className={`cursor-pointer bg-white p-4 rounded-xl border transition-all ${
            activeTab === "PAUSED" ? "border-blue-500 ring-2 ring-blue-500/20 shadow" : "border-slate-200 hover:border-slate-300"
          }`}
        >
          <div className="text-xs font-semibold text-blue-700 flex items-center justify-between">
            <span>Paused Clocks</span>
            <PauseCircle className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-black text-blue-800 mt-1">{pausedCount}</div>
          <div className="text-[11px] text-blue-600 mt-1">Awaiting clarification</div>
        </div>

        <div
          onClick={() => setActiveTab("OVERDUE")}
          className={`cursor-pointer bg-white p-4 rounded-xl border transition-all ${
            activeTab === "OVERDUE" ? "border-rose-500 ring-2 ring-rose-500/20 shadow" : "border-slate-200 hover:border-slate-300"
          }`}
        >
          <div className="text-xs font-semibold text-rose-700 flex items-center justify-between">
            <span>Breached / Overdue</span>
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          <div className="text-2xl font-black text-rose-800 mt-1">{overdueCount}</div>
          <div className="text-[11px] text-rose-600 mt-1">Escalated to bureau</div>
        </div>

        <div
          onClick={() => setActiveTab("MET")}
          className={`cursor-pointer bg-white p-4 rounded-xl border transition-all ${
            activeTab === "MET" ? "border-slate-800 ring-2 ring-slate-800/20 shadow" : "border-slate-200 hover:border-slate-300"
          }`}
        >
          <div className="text-xs font-semibold text-slate-700 flex items-center justify-between">
            <span>Completed (MET)</span>
            <CheckCircle2 className="w-4 h-4 text-slate-700" />
          </div>
          <div className="text-2xl font-black text-slate-900 mt-1">{metCount}</div>
          <div className="text-[11px] text-slate-500 mt-1">Verified & stopped</div>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Controls Toolbar */}
        <div className="p-4 border-b border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-50/50">
          <div className="flex items-center gap-2">
            {["ALL", "RUNNING", "PAUSED", "OVERDUE", "MET"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                  activeTab === tab
                    ? "bg-[#0B2545] text-white"
                    : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
                }`}
              >
                {tab.replace("_", " ")}
              </button>
            ))}
          </div>

          <div className="relative w-full md:w-72">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by ID, title, institute..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#1677C8]"
            />
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <th className="py-3 px-4">Obligation No</th>
                <th className="py-3 px-4">Title & Subject</th>
                <th className="py-3 px-4">Responsible Entity</th>
                <th className="py-3 px-4">APH Clause</th>
                <th className="py-3 px-4">Due Date</th>
                <th className="py-3 px-4">Clock State</th>
                <th className="py-3 px-4">Escalation</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500 font-medium">
                    Loading Promise Ledger records...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500">
                    No obligations found matching current filter.
                  </td>
                </tr>
              ) : (
                filtered.map((obl) => {
                  const isOverdue = obl.days_remaining < 0 && obl.status !== "MET";
                  return (
                    <tr key={obl.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-[#1677C8]">
                        {obl.obligation_no}
                      </td>
                      <td className="py-3 px-4 max-w-xs">
                        <div className="font-bold text-slate-900 truncate">{obl.title}</div>
                        <div className="text-[11px] text-slate-500 truncate">{obl.institution_name}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-slate-900">{obl.responsible_post}</div>
                        <div className="text-[10px] text-slate-500">{obl.responsible_role}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-[11px] text-slate-700">
                          {obl.aph_clause}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-900">
                          {new Date(obl.due_date).toLocaleDateString()}
                        </div>
                        <div
                          className={`text-[10px] font-bold ${
                            isOverdue
                              ? "text-rose-600"
                              : obl.days_remaining <= 3
                              ? "text-amber-600"
                              : "text-slate-500"
                          }`}
                        >
                          {obl.status === "MET"
                            ? "Completed"
                            : isOverdue
                            ? `Breached (${Math.abs(obl.days_remaining)}d ago)`
                            : `${obl.days_remaining}d remaining`}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        {obl.clock_state === "RUNNING" && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                            RUNNING
                          </span>
                        )}
                        {obl.clock_state?.startsWith("PAUSED") && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                            <PauseCircle className="w-3 h-3 text-blue-600" />
                            PAUSED ({obl.total_paused_days}d)
                          </span>
                        )}
                        {obl.clock_state === "BREACHED" && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">
                            <AlertTriangle className="w-3 h-3 text-rose-600" />
                            BREACHED
                          </span>
                        )}
                        {obl.clock_state === "STOPPED_MET" && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-800">
                            <CheckCircle2 className="w-3 h-3 text-slate-600" />
                            MET
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {obl.escalation_level > 0 ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                            Level {obl.escalation_level}
                          </span>
                        ) : (
                          <span className="text-slate-400 text-[11px]">Normal</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Phase 5 Why Button */}
                          <button
                            onClick={() => openWhyModal(obl.id)}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded bg-[#1677C8]/10 hover:bg-[#1677C8]/20 text-[#1677C8] text-[11px] font-bold transition-colors"
                            title="View Phase 5 Mathematical & Statutory Breakdown"
                          >
                            <HelpCircle className="w-3.5 h-3.5" />
                            Why?
                          </button>

                          {isOfficer && obl.status !== "MET" && (
                            <>
                              {obl.clock_state === "RUNNING" ? (
                                <button
                                  onClick={() => {
                                    setSelectedObligationId(obl.id);
                                    setPauseModalOpen(true);
                                  }}
                                  className="p-1 rounded text-slate-600 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                                  title="Pause Clock"
                                >
                                  <PauseCircle className="w-4 h-4" />
                                </button>
                              ) : obl.clock_state?.startsWith("PAUSED") ? (
                                <button
                                  onClick={() => handleResumeClock(obl.id)}
                                  className="p-1 rounded text-slate-600 hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
                                  title="Resume Clock"
                                >
                                  <PlayCircle className="w-4 h-4" />
                                </button>
                              ) : null}

                              <button
                                onClick={() => {
                                  setSelectedObligationId(obl.id);
                                  setExtensionModalOpen(true);
                                }}
                                className="p-1 rounded text-slate-600 hover:text-amber-600 hover:bg-amber-50 transition-colors"
                                title="Grant Extension"
                              >
                                <Calendar className="w-4 h-4" />
                              </button>

                              <button
                                onClick={() => handleCompleteObligation(obl.id)}
                                className="p-1 rounded text-slate-600 hover:text-emerald-600 hover:bg-emerald-50 transition-colors"
                                title="Mark Complete (MET)"
                              >
                                <CheckCircle2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Phase 5 "Why?" Modal */}
      {selectedObligationId && (
        <WhyExplanationModal
          isOpen={whyModalOpen}
          onClose={() => setWhyModalOpen(false)}
          entityType="obligation"
          entityId={selectedObligationId}
        />
      )}

      {/* Pause Clock Modal */}
      {pauseModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-base font-bold text-slate-900 mb-2">Pause Processing Clock</h3>
            <p className="text-xs text-slate-600 mb-4">
              Pauses the active statutory scrutiny clock. Clock state will transition to PAUSED_INSTITUTION.
            </p>
            <label className="text-xs font-bold text-slate-700 block mb-1">
              Mandatory Pause Reason:
            </label>
            <textarea
              rows={3}
              value={actionReason}
              onChange={(e) => setActionReason(e.target.value)}
              placeholder="e.g. Returned to institution for Fire NOC clarification."
              className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-[#1677C8] mb-4"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setPauseModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handlePauseClock}
                disabled={actionLoading || !actionReason.trim()}
                className="px-4 py-1.5 text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
              >
                {actionLoading ? "Pausing..." : "Confirm Pause"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Extension Modal */}
      {extensionModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-base font-bold text-slate-900 mb-2">Grant Statutory Extension</h3>
            <p className="text-xs text-slate-600 mb-4">
              Extends the calculated due date by approved working or calendar days.
            </p>
            <div className="space-y-3 mb-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Additional Days:
                </label>
                <input
                  type="number"
                  min={1}
                  max={60}
                  value={extensionDays}
                  onChange={(e) => setExtensionDays(parseInt(e.target.value) || 1)}
                  className="w-full text-xs p-2.5 border border-slate-300 rounded-lg"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Statutory Approval Justification:
                </label>
                <textarea
                  rows={3}
                  value={actionReason}
                  onChange={(e) => setActionReason(e.target.value)}
                  placeholder="e.g. Approved by Regional Committee under APH 2024-27 Clause 2.7."
                  className="w-full text-xs p-2.5 border border-slate-300 rounded-lg"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setExtensionModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleGrantExtension}
                disabled={actionLoading || !actionReason.trim()}
                className="px-4 py-1.5 text-xs font-bold bg-[#1677C8] hover:bg-[#123B63] text-white rounded-lg disabled:opacity-50"
              >
                {actionLoading ? "Extending..." : "Confirm Extension"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
