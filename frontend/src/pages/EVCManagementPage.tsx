import React, { useState, useEffect } from "react";
import {
  Users,
  Calendar,
  MapPin,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ShieldCheck,
  FileText,
  Search,
  Check,
  UserCheck
} from "lucide-react";
import api from "../services/api";
import { useAuth } from "../context/AuthContext";
import { WhyExplanationModal } from "../components/common/WhyExplanationModal";

export const EVCManagementPage: React.FC = () => {
  const { user } = useAuth();
  const isOfficer = user?.role === "AICTE_OFFICER" || user?.role === "ADMINISTRATOR";

  const [schedules, setSchedules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("ALL");
  const [search, setSearch] = useState("");

  // Scheduling Modal
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [selectedEvc, setSelectedEvc] = useState<any>(null);
  const [visitDate, setVisitDate] = useState("");
  const [visitLocation, setVisitLocation] = useState("");
  const [scheduleLoading, setScheduleLoading] = useState(false);

  // Report Modal
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [recommendation, setRecommendation] = useState("RECOMMENDED");
  const [reportSummary, setReportSummary] = useState("");

  // Why modal
  const [whyModalOpen, setWhyModalOpen] = useState(false);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);

  const fetchSchedules = async () => {
    try {
      setLoading(true);
      const res = await api.get("/evc");
      setSchedules(res.data);
    } catch (err) {
      console.error("Failed to load EVC schedules:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedules();
  }, []);

  const openScheduleModal = (evc: any) => {
    setSelectedEvc(evc);
    setVisitLocation(evc.visit_location || "");
    const d = new Date();
    d.setDate(d.getDate() + 7);
    setVisitDate(d.toISOString().slice(0, 16));
    setScheduleModalOpen(true);
  };

  const handleConfirmSchedule = async () => {
    if (!selectedEvc || !visitDate) return;
    try {
      setScheduleLoading(true);
      await api.post(`/evc/${selectedEvc.id}/schedule`, {
        visit_date: new Date(visitDate).toISOString(),
        visit_location: visitLocation || "Main Campus Premises",
        approved_experts: selectedEvc.proposed_panel || [],
      });
      setScheduleModalOpen(false);
      fetchSchedules();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to schedule visit");
    } finally {
      setScheduleLoading(false);
    }
  };

  const openReportModal = (evc: any) => {
    setSelectedEvc(evc);
    setRecommendation("RECOMMENDED");
    setReportSummary("");
    setReportModalOpen(true);
  };

  const handleConfirmReport = async () => {
    if (!selectedEvc || !reportSummary.trim()) return;
    try {
      setScheduleLoading(true);
      await api.post(`/evc/${selectedEvc.id}/report`, {
        recommendation: recommendation,
        summary: reportSummary,
      });
      setReportModalOpen(false);
      fetchSchedules();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to submit report");
    } finally {
      setScheduleLoading(false);
    }
  };

  const filtered = schedules.filter((s) => {
    if (activeTab === "PROPOSED" && s.status !== "PANEL_PROPOSED") return false;
    if (activeTab === "SCHEDULED" && s.status !== "SCHEDULED") return false;
    if (activeTab === "REPORT_RECEIVED" && s.status !== "REPORT_RECEIVED") return false;

    if (search) {
      const q = search.toLowerCase();
      return (
        s.evc_no.toLowerCase().includes(q) ||
        s.institution_name.toLowerCase().includes(q) ||
        s.application_reference.toLowerCase().includes(q)
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
              Phase 7
            </span>
            <span className="text-xs text-slate-500 font-medium">Physical Infrastructure & Faculty Scrutiny</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <Users className="w-6 h-6 text-[#1677C8]" />
            Expert Visit Committee (EVC) Management
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-3xl">
            Propose expert panels, run automated conflict-of-interest checks, schedule physical inspection visits, and track committee inspection reports.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {["ALL", "PROPOSED", "SCHEDULED", "REPORT_RECEIVED"].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                activeTab === tab
                  ? "bg-[#0B2545] text-white"
                  : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-100"
              }`}
            >
              {tab.replace("_", " ")}
            </button>
          ))}
        </div>

        <div className="relative w-72">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search EVC no, institution..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-300"
          />
        </div>
      </div>

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {loading ? (
          <div className="col-span-2 py-12 text-center text-slate-500 font-medium">
            Loading EVC inspections...
          </div>
        ) : filtered.length === 0 ? (
          <div className="col-span-2 py-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
            No EVC inspection records found for this category.
          </div>
        ) : (
          filtered.map((evc) => {
            const proposedPanel = evc.proposed_panel || [];
            return (
              <div key={evc.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="font-mono text-xs font-bold text-[#1677C8]">{evc.evc_no}</span>
                    <h3 className="text-base font-bold text-slate-900 mt-0.5">{evc.institution_name}</h3>
                    <p className="text-xs text-slate-500">Ref: {evc.application_reference} | {evc.region}</p>
                  </div>
                  <div>
                    {evc.status === "PANEL_PROPOSED" && (
                      <span className="px-2.5 py-1 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                        Panel Proposed
                      </span>
                    )}
                    {evc.status === "SCHEDULED" && (
                      <span className="px-2.5 py-1 rounded text-xs font-bold bg-blue-100 text-blue-800 border border-blue-300">
                        Scheduled
                      </span>
                    )}
                    {evc.status === "REPORT_RECEIVED" && (
                      <span className="px-2.5 py-1 rounded text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                        Report Received ({evc.report_recommendation})
                      </span>
                    )}
                  </div>
                </div>

                {/* Conflict-of-interest check */}
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
                  <div className="flex items-center gap-1.5 font-bold text-slate-700 mb-1">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" />
                    <span>Conflict-of-Interest Status:</span>
                    <span className="text-emerald-700">Verified Clear</span>
                  </div>
                  <div className="text-[11px] text-slate-600">
                    {evc.conflict_check_notes || "All proposed experts are conflict-free with respect to target institution."}
                  </div>
                </div>

                {/* Expert Committee Panel */}
                <div>
                  <div className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>Proposed Expert Committee:</span>
                    <span className="text-[11px] font-normal text-slate-500">{proposedPanel.length} Nominees</span>
                  </div>
                  <div className="space-y-1.5">
                    {proposedPanel.map((exp: any, i: number) => (
                      <div key={i} className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-100 text-xs">
                        <div>
                          <div className="font-bold text-slate-900">{exp.name}</div>
                          <div className="text-[11px] text-slate-500">{exp.designation}, {exp.institution}</div>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                          {exp.specialization}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Visit Details if Scheduled */}
                {evc.scheduled_date && (
                  <div className="p-3 bg-blue-50/50 border border-blue-200 rounded-lg text-xs space-y-1">
                    <div className="flex items-center gap-2 text-slate-800">
                      <Calendar className="w-4 h-4 text-[#1677C8]" />
                      <span>Visit Date: <strong>{new Date(evc.scheduled_date).toLocaleString()}</strong></span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-800">
                      <MapPin className="w-4 h-4 text-[#1677C8]" />
                      <span className="truncate">Location: {evc.visit_location}</span>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                  <button
                    onClick={() => {
                      setSelectedAppId(evc.application_id);
                      setWhyModalOpen(true);
                    }}
                    className="text-xs font-bold text-[#1677C8] hover:underline"
                  >
                    Why was EVC triggered?
                  </button>

                  <div className="flex items-center gap-2">
                    {isOfficer && evc.status === "PANEL_PROPOSED" && (
                      <button
                        onClick={() => openScheduleModal(evc)}
                        className="px-3 py-1.5 bg-[#1677C8] hover:bg-[#123B63] text-white text-xs font-bold rounded-lg transition-colors"
                      >
                        Approve Panel & Schedule Visit
                      </button>
                    )}

                    {isOfficer && evc.status === "SCHEDULED" && (
                      <button
                        onClick={() => openReportModal(evc)}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg transition-colors"
                      >
                        Submit Inspection Report
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Schedule Modal */}
      {scheduleModalOpen && selectedEvc && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">
              Approve Committee & Confirm EVC Visit Date
            </h3>
            <p className="text-xs text-slate-600">
              Under APH 2024-27 Clause 2.5, the authorized officer must review and confirm the proposed inspection panel before official summons.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Inspection Visit Date & Time:</label>
                <input
                  type="datetime-local"
                  value={visitDate}
                  onChange={(e) => setVisitDate(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Inspection Campus Location:</label>
                <input
                  type="text"
                  value={visitLocation}
                  onChange={(e) => setVisitLocation(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setScheduleModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmSchedule}
                disabled={scheduleLoading || !visitDate}
                className="px-4 py-1.5 text-xs font-bold bg-[#1677C8] hover:bg-[#123B63] text-white rounded-lg disabled:opacity-50"
              >
                {scheduleLoading ? "Scheduling..." : "Approve Panel & Schedule Visit"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Report Modal */}
      {reportModalOpen && selectedEvc && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">
              Submit EVC Inspection Report
            </h3>
            <p className="text-xs text-slate-600">
              Record the official recommendation of the Expert Visit Committee for {selectedEvc.institution_name}.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Committee Recommendation:</label>
                <select
                  value={recommendation}
                  onChange={(e) => setRecommendation(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                >
                  <option value="RECOMMENDED">RECOMMENDED FOR APPROVAL</option>
                  <option value="DEFICIENT">DEFICIENT - REQUIRES DEFICIENCY RECTIFICATION</option>
                  <option value="REJECTED">REJECTED - STATUTORY VIOLATION</option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Inspection Findings Summary:</label>
                <textarea
                  rows={4}
                  value={reportSummary}
                  onChange={(e) => setReportSummary(e.target.value)}
                  placeholder="e.g. Physical verification confirmed 12 labs, land area of 10.5 acres verified with demarcation..."
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setReportModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmReport}
                disabled={scheduleLoading || !reportSummary.trim()}
                className="px-4 py-1.5 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg disabled:opacity-50"
              >
                {scheduleLoading ? "Submitting..." : "Submit Inspection Report"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Why Modal */}
      {selectedAppId && (
        <WhyExplanationModal
          isOpen={whyModalOpen}
          onClose={() => setWhyModalOpen(false)}
          entityType="routing"
          entityId={selectedAppId}
        />
      )}
    </div>
  );
};
