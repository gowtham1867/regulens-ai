import React, { useState, useEffect } from "react";
import {
  Settings,
  Calendar,
  Layers,
  Activity,
  Plus,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCw
} from "lucide-react";
import api from "../services/api";

export const AdminWorkflowConfigPage: React.FC = () => {
  const [routeTemplates, setRouteTemplates] = useState<any[]>([]);
  const [holidays, setHolidays] = useState<any[]>([]);
  const [schedulerJobs, setSchedulerJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Holiday Modal
  const [holidayModalOpen, setHolidayModalOpen] = useState(false);
  const [holidayName, setHolidayName] = useState("");
  const [holidayDate, setHolidayDate] = useState("");
  const [holidayRegion, setHolidayRegion] = useState("ALL");
  const [submitting, setSubmitting] = useState(false);

  // Scan triggering
  const [scanResult, setScanResult] = useState<any>(null);
  const [scanning, setScanning] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [tmplRes, holRes, jobRes] = await Promise.all([
        api.get("/admin-config/route-templates"),
        api.get("/admin-config/holidays"),
        api.get("/admin-config/scheduler-status"),
      ]);
      setRouteTemplates(tmplRes.data);
      setHolidays(holRes.data);
      setSchedulerJobs(jobRes.data);
    } catch (err) {
      console.error("Failed to load admin configs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAddHoliday = async () => {
    if (!holidayName || !holidayDate) return;
    try {
      setSubmitting(true);
      await api.post("/admin-config/holidays", {
        name: holidayName,
        date: new Date(holidayDate).toISOString(),
        region: holidayRegion,
        is_statutory: true,
      });
      setHolidayModalOpen(false);
      setHolidayName("");
      loadData();
    } catch (err) {
      alert("Failed to add statutory holiday.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleTriggerScan = async () => {
    try {
      setScanning(true);
      const res = await api.post("/admin-config/trigger-escalation-scan");
      setScanResult(res.data);
      loadData();
    } catch (err) {
      alert("Failed to trigger automated scan.");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-[#1677C8]/10 text-[#1677C8]">
              Phase 11 & 15
            </span>
            <span className="text-xs text-slate-500 font-medium">Administrator Governance</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <Settings className="w-6 h-6 text-[#1677C8]" />
            Workflow Routes & Deterministic Clock Engine Configuration
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-3xl">
            Configure statutory approval paths, stage timelines, regional gazetted holiday exclusion calendars, and background scheduler tasks.
          </p>
        </div>

        <button
          onClick={handleTriggerScan}
          disabled={scanning}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition-all disabled:opacity-50"
        >
          <Play className="w-4 h-4" />
          {scanning ? "Evaluating Deadlines..." : "Trigger Deadline Escalation Scan"}
        </button>
      </div>

      {scanResult && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-xs text-emerald-900">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <span>
              Escalation Scan Executed: Evaluated <strong>{scanResult.total_active_evaluated}</strong> active obligations. 
              Triggered <strong>{scanResult.escalated_count}</strong> statutory breach escalations and <strong>{scanResult.reminded_count}</strong> reminders.
            </span>
          </div>
          <button onClick={() => setScanResult(null)} className="font-bold underline text-emerald-800">Dismiss</button>
        </div>
      )}

      {/* Background Scheduler Status */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <Activity className="w-4 h-4 text-[#1677C8]" />
            Persistent Background Scheduler Jobs (Phase 15)
          </div>
          <span className="text-xs text-emerald-700 font-bold bg-emerald-50 px-2.5 py-0.5 rounded border border-emerald-200">
            Engine Online
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {schedulerJobs.map((job) => (
            <div key={job.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-slate-900">{job.job_name}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                  {job.status}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 font-medium">Type: {job.job_type} | Interval: {job.interval_seconds}s</div>
              <div className="text-[11px] text-slate-700 bg-white p-2 rounded border border-slate-200 truncate">
                {job.last_result || "Awaiting first execution tick"}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Configured Route Templates */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <Layers className="w-4 h-4 text-[#1677C8]" />
            Statutory Approval Route Templates (Phase 3)
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <th className="py-3 px-4">Application Category</th>
                <th className="py-3 px-4">Assigned Statutory Route</th>
                <th className="py-3 px-4">Stage Sequence</th>
                <th className="py-3 px-4">Scrutiny Days</th>
                <th className="py-3 px-4">EVC Days</th>
                <th className="py-3 px-4">Clarification Days</th>
                <th className="py-3 px-4">Version</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {routeTemplates.map((t) => (
                <tr key={t.id} className="hover:bg-slate-50/80">
                  <td className="py-3 px-4 font-bold text-slate-900">{t.category}</td>
                  <td className="py-3 px-4 font-mono font-bold text-[#1677C8]">{t.route_type}</td>
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-1 flex-wrap">
                      {t.stages?.map((s: string, idx: number) => (
                        <span key={idx} className="bg-slate-100 px-1.5 py-0.5 rounded text-[10px] text-slate-700">
                          {s}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-4 font-semibold">{t.default_scrutiny_days}d</td>
                  <td className="py-3 px-4 font-semibold">{t.default_evc_days}d</td>
                  <td className="py-3 px-4 font-semibold">{t.default_institution_clarification_days}d</td>
                  <td className="py-3 px-4 text-slate-500 font-mono">v{t.version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Statutory Holiday Calendar */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <Calendar className="w-4 h-4 text-[#1677C8]" />
            Statutory Gazetted Holiday Calendars (Phase 4 Working Day Exclusions)
          </div>
          <button
            onClick={() => setHolidayModalOpen(true)}
            className="inline-flex items-center gap-1 px-3 py-1.5 bg-[#1677C8] hover:bg-[#123B63] text-white text-xs font-bold rounded-lg transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Holiday
          </button>
        </div>

        <div className="overflow-x-auto max-h-64">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200 sticky top-0">
              <tr>
                <th className="py-2.5 px-4">Date</th>
                <th className="py-2.5 px-4">Holiday Name</th>
                <th className="py-2.5 px-4">Applicable Region</th>
                <th className="py-2.5 px-4">Type</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-800">
              {holidays.map((h) => (
                <tr key={h.id} className="hover:bg-slate-50/80">
                  <td className="py-2.5 px-4 font-bold text-slate-900">
                    {new Date(h.date).toLocaleDateString()}
                  </td>
                  <td className="py-2.5 px-4 font-semibold text-slate-900">{h.name}</td>
                  <td className="py-2.5 px-4">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700">
                      {h.region}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-emerald-700 font-semibold">Statutory Gazetted</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Holiday Modal */}
      {holidayModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-slate-900">Add Statutory Gazetted Holiday</h3>
            <p className="text-xs text-slate-600">
              This date will be deterministically excluded from working day deadline calculations.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">Holiday Name:</label>
                <input
                  type="text"
                  value={holidayName}
                  onChange={(e) => setHolidayName(e.target.value)}
                  placeholder="e.g. Eid-ul-Fitr, Good Friday"
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Calendar Date:</label>
                <input
                  type="date"
                  value={holidayDate}
                  onChange={(e) => setHolidayDate(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Applicable Region:</label>
                <select
                  value={holidayRegion}
                  onChange={(e) => setHolidayRegion(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg"
                >
                  <option value="ALL">All India (National Gazetted)</option>
                  <option value="SOUTHERN">Southern Regional Directorate</option>
                  <option value="NORTHERN">Northern Regional Directorate</option>
                  <option value="WESTERN">Western Regional Directorate</option>
                  <option value="EASTERN">Eastern Regional Directorate</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setHolidayModalOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleAddHoliday}
                disabled={submitting || !holidayName || !holidayDate}
                className="px-4 py-1.5 text-xs font-bold bg-[#1677C8] hover:bg-[#123B63] text-white rounded-lg disabled:opacity-50"
              >
                {submitting ? "Adding..." : "Confirm Holiday"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
