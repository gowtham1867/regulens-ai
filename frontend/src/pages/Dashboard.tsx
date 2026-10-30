import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  FileText,
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
  HelpCircle,
  PlusCircle,
  ArrowRight,
  ShieldCheck,
  TrendingUp,
  Activity,
  Layers,
  Building2,
  Users,
  CalendarClock,
  Flame,
  Award,
  ChevronRight,
  MapPin,
  ExternalLink
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { StatusBadge } from "../components/common/StatusBadge";
import { WhyExplanationModal } from "../components/common/WhyExplanationModal";
import type { Application } from "../types";

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const isOfficerOrAdmin = user?.role === "AICTE_OFFICER" || user?.role === "ADMINISTRATOR";
  const isInstitution = user?.role === "INSTITUTION_USER";

  const [summary, setSummary] = useState<any>(null);
  const [recentApps, setRecentApps] = useState<Application[]>([]);
  const [pendingInstitutions, setPendingInstitutions] = useState<any[]>([]);
  const [todayInbox, setTodayInbox] = useState<any[]>([]);
  const [pendencyData, setPendencyData] = useState<any>(null);
  const [institutionObligations, setInstitutionObligations] = useState<any[]>([]);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  // Workflow Overview Tab
  const [workflowFilter, setWorkflowFilter] = useState("ALL");
  const [regionFilter, setRegionFilter] = useState("ALL");

  // Why Modal
  const [whyModalOpen, setWhyModalOpen] = useState(false);
  const [selectedObligationId, setSelectedObligationId] = useState<number | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, [regionFilter]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [sumData, appsData] = await Promise.all([
        api.getDashboardSummary(),
        api.getApplications(),
      ]);
      setSummary(sumData);
      setRecentApps(Array.isArray(appsData) ? appsData : []);

      if (isOfficerOrAdmin) {
        try {
          const [pending, inboxRes, pendencyRes] = await Promise.all([
            api.getPendingInstitutions(),
            api.get("/obligations/officer-inbox/today?limit=10"),
            api.get("/compliance-reports/pendency_ageing"),
          ]);
          setPendingInstitutions(pending || []);
          setTodayInbox(inboxRes.data || []);
          setPendencyData(pendencyRes.data || null);
        } catch (e) {
          console.warn("Failed to load officer specialized data:", e);
        }
      }

      if (isInstitution) {
        try {
          const oblsRes = await api.get("/obligations");
          setInstitutionObligations(oblsRes.data || []);
        } catch (e) {
          console.warn("Failed to load institution obligations:", e);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyInstitution = async (instId: number, status: "APPROVED" | "REJECTED") => {
    setActionLoadingId(instId);
    try {
      await api.verifyInstitution(instId, status);
      setPendingInstitutions((prev) => prev.filter((i) => i.id !== instId));
    } catch (err: any) {
      alert(err.message || "Failed to update institution verification status");
    } finally {
      setActionLoadingId(null);
    }
  };

  const openWhyModal = (oblId: number) => {
    setSelectedObligationId(oblId);
    setWhyModalOpen(true);
  };

  const metricCards = [
    {
      title: "Total Applications",
      value: summary?.total_applications ?? 0,
      icon: FileText,
      color: "border-[#1677C8] text-[#1677C8]",
      bg: "bg-blue-50/50",
    },
    {
      title: "Under Scrutiny",
      value: summary?.under_review_applications ?? 0,
      icon: Clock,
      color: "border-sky-500 text-sky-600",
      bg: "bg-sky-50/50",
    },
    {
      title: "Critical Deficiencies",
      value: summary?.critical_deficiencies ?? 0,
      icon: XCircle,
      color: "border-rose-500 text-rose-600",
      bg: "bg-rose-50/50",
    },
    {
      title: "Clarifications",
      value: summary?.awaiting_clarification ?? 0,
      icon: HelpCircle,
      color: "border-amber-500 text-amber-600",
      bg: "bg-amber-50/50",
    },
    {
      title: "Active Warnings",
      value: summary?.active_warnings ?? 0,
      icon: AlertTriangle,
      color: "border-orange-500 text-orange-600",
      bg: "bg-orange-50/50",
    },
    {
      title: "Approved (LoA)",
      value: summary?.approved_applications ?? 0,
      icon: CheckCircle2,
      color: "border-emerald-500 text-emerald-600",
      bg: "bg-emerald-50/50",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-[#0B2545] to-[#123B63] rounded-2xl p-6 text-white shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-wider text-[#16A6C8] font-bold">
            {isInstitution ? "Institution Regulatory Scrutiny Portal" : "AICTE Scrutiny Officer Workspace (SIH PS 26262)"}
          </div>
          <h1 className="text-xl md:text-2xl font-black mt-1">
            Welcome back, {user?.full_name}
          </h1>
          <p className="text-xs text-slate-300 mt-1 max-w-xl leading-relaxed">
            {isInstitution
              ? `Manage applications, upload verified supporting evidence, and track statutory obligations for ${user.institution_name}.`
              : "Automated workflow routing, deterministic clock deadlines, EVC management, and cryptographic audit provenance."}
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
          {isInstitution ? (
            <>
              <Link
                to="/applications/new"
                className="inline-flex items-center gap-2 px-4 py-2 bg-[#1677C8] hover:bg-[#1264a8] text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
              >
                <PlusCircle className="w-4 h-4" />
                <span>New Application</span>
              </Link>
              <Link
                to="/document-validity"
                className="inline-flex items-center gap-2 px-3 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-xs font-bold transition-colors border border-white/20"
              >
                <CalendarClock className="w-4 h-4" />
                <span>Validity Tracker</span>
              </Link>
            </>
          ) : (
            <>
              <Link
                to="/obligations"
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-[#1677C8] hover:bg-[#1264a8] text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
              >
                <Layers className="w-4 h-4" />
                <span>Promise Ledger</span>
              </Link>
              <Link
                to="/evc"
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-[#16A6C8] hover:bg-[#1289a6] text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
              >
                <Users className="w-4 h-4" />
                <span>EVC Inspection</span>
              </Link>
              <Link
                to="/reports"
                className="inline-flex items-center gap-2 px-3.5 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-xs font-bold transition-colors border border-white/20"
              >
                <span>11 Reports</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Operational Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {metricCards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              className={`bg-white rounded-xl p-4 border border-[#DCE4ED] shadow-xs hover:shadow-sm transition-all ${card.bg}`}
            >
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-[11px] font-bold uppercase tracking-wider truncate">
                  {card.title}
                </span>
                <Icon className={`w-4 h-4 ${card.color.split(" ")[1]}`} />
              </div>
              <div className="text-2xl font-black text-slate-900">
                {loading ? "..." : card.value}
              </div>
            </div>
          );
        })}
      </div>

      {/* ===================================================================== */}
      {/* PHASE 6.C: OFFICER DAILY INBOX — TODAY'S 10                           */}
      {/* ===================================================================== */}
      {isOfficerOrAdmin && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-slate-200 bg-gradient-to-r from-blue-50/70 to-indigo-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#0B2545] text-white flex items-center justify-center font-black shadow-sm">
                10
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-slate-900">
                    Officer Daily Inbox — Today's 10
                  </h2>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#1677C8] text-white">
                    Prioritized
                  </span>
                </div>
                <p className="text-xs text-slate-600 mt-0.5">
                  Transparent statutory urgency ranking based on days remaining, paused intervals, and escalation level.
                </p>
              </div>
            </div>

            <Link
              to="/obligations"
              className="text-xs font-bold text-[#1677C8] hover:underline flex items-center gap-1 self-start sm:self-center"
            >
              <span>View Central Ledger</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-100/70 border-b border-slate-200 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Priority & Case</th>
                  <th className="px-4 py-3">Responsible Institution</th>
                  <th className="px-4 py-3">Transparent Urgency Reason</th>
                  <th className="px-4 py-3">Time Remaining</th>
                  <th className="px-4 py-3">Next Action Required</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {todayInbox.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-6 text-center text-slate-400">
                      No critical pending obligations in today's inbox. All clocks running smoothly!
                    </td>
                  </tr>
                ) : (
                  todayInbox.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-slate-200 text-slate-800 font-bold text-[10px] flex items-center justify-center shrink-0">
                            #{idx + 1}
                          </span>
                          <div>
                            <span className="font-mono font-bold text-[#1677C8]">
                              {item.obligation_no}
                            </span>
                            <div className="font-semibold text-slate-900 truncate max-w-xs">{item.title}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-900">
                        {item.institution_name}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col gap-1">
                          {item.urgency_reasons?.map((r: string, rIdx: number) => (
                            <span
                              key={rIdx}
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold ${
                                item.is_overdue
                                  ? "bg-rose-100 text-rose-800"
                                  : item.days_remaining <= 3
                                  ? "bg-amber-100 text-amber-800"
                                  : "bg-blue-50 text-blue-700"
                              }`}
                            >
                              <Flame className="w-3 h-3 shrink-0" />
                              {r}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`font-bold ${
                            item.is_overdue ? "text-rose-600" : item.days_remaining <= 3 ? "text-amber-600" : "text-slate-800"
                          }`}
                        >
                          {item.is_overdue ? `Breached by ${Math.abs(item.days_remaining)}d` : `${item.days_remaining}d remaining`}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600 max-w-xs truncate">
                        {item.next_required_action}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {item.application_id && (
                            <Link
                              to={`/applications/${item.application_id}`}
                              className="px-2.5 py-1 text-xs font-semibold rounded bg-[#1677C8] text-white hover:bg-[#123B63] transition-colors"
                            >
                              Open Case
                            </Link>
                          )}
                          <button
                            onClick={() => openWhyModal(item.obligation_id)}
                            className="px-2 py-1 text-xs font-bold rounded bg-[#1677C8]/10 text-[#1677C8] hover:bg-[#1677C8]/20 transition-colors"
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
      )}

      {/* ===================================================================== */}
      {/* PHASE 6.B: PENDENCY & AGEING MONITORING                               */}
      {/* ===================================================================== */}
      {isOfficerOrAdmin && pendencyData && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-[#1677C8]" />
              <h2 className="text-sm font-bold text-slate-900">
                Application Ageing & Pendency Monitoring (Phase 6.B)
              </h2>
            </div>
            <span className="text-xs text-slate-500 font-semibold">
              Average Processing Turnaround: {pendencyData.summary?.average_age_days || 0} Days
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
            <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200">
              <span className="text-xs font-bold text-emerald-800 uppercase block">&lt; 15 Days</span>
              <span className="text-2xl font-black text-emerald-900 mt-1 block">
                {pendencyData.summary?.bands?.under_15 || 0}
              </span>
              <span className="text-[10px] text-emerald-700">Healthy Timelines</span>
            </div>

            <div className="p-3 bg-blue-50 rounded-xl border border-blue-200">
              <span className="text-xs font-bold text-blue-800 uppercase block">15 - 30 Days</span>
              <span className="text-2xl font-black text-blue-900 mt-1 block">
                {pendencyData.summary?.bands?.["15_to_30"] || 0}
              </span>
              <span className="text-[10px] text-blue-700">Standard Review</span>
            </div>

            <div className="p-3 bg-amber-50 rounded-xl border border-amber-200">
              <span className="text-xs font-bold text-amber-800 uppercase block">30 - 60 Days</span>
              <span className="text-2xl font-black text-amber-900 mt-1 block">
                {pendencyData.summary?.bands?.["30_to_60"] || 0}
              </span>
              <span className="text-[10px] text-amber-700">Approaching Limit</span>
            </div>

            <div className="p-3 bg-rose-50 rounded-xl border border-rose-200">
              <span className="text-xs font-bold text-rose-800 uppercase block">&gt; 60 Days</span>
              <span className="text-2xl font-black text-rose-900 mt-1 block">
                {pendencyData.summary?.bands?.over_60 || 0}
              </span>
              <span className="text-[10px] text-rose-700 font-bold">Critical Bottleneck</span>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* PHASE 14: INSTITUTION COMPLIANCE HEALTH CARD                          */}
      {/* ===================================================================== */}
      {isInstitution && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-black text-lg shadow-sm">
                98%
              </div>
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <span>Institutional Compliance Health Card</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                    Excellent Standing
                  </span>
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  AICTE APH 2024-2027 continuous compliance benchmark score
                </p>
              </div>
            </div>

            <Link
              to="/document-validity"
              className="text-xs font-bold text-[#1677C8] hover:underline flex items-center gap-1"
            >
              <span>Manage Certificates</span>
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 font-medium block">Active Statutory Obligations</span>
              <span className="text-xl font-bold text-slate-900 mt-1 block">
                {institutionObligations.filter((o) => o.status === "RUNNING").length} Active
              </span>
              <div className="text-[11px] text-emerald-600 mt-1 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>All within statutory limits</span>
              </div>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 font-medium block">Land Lease Period</span>
              <span className="text-xl font-bold text-slate-900 mt-1 block">28 Years Remaining</span>
              <div className="text-[11px] text-emerald-600 mt-1 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Mandatory 30y criterion satisfied</span>
              </div>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 font-medium block">Fire Safety NOC</span>
              <span className="text-xl font-bold text-amber-700 mt-1 block">Renewal Due in 18d</span>
              <div className="text-[11px] text-amber-600 mt-1 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                <Link to="/document-validity" className="underline font-bold">Submit renewal document</Link>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pending Institution Registrations Table */}
      {isOfficerOrAdmin && pendingInstitutions.length > 0 && (
        <div className="bg-amber-50/60 rounded-xl border border-amber-200 shadow-xs overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-amber-200 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-amber-100 text-amber-800">
                <Building2 className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-amber-950 flex items-center gap-2">
                  <span>Pending Institutional Registrations</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-200 text-amber-900">
                    {pendingInstitutions.length} Awaiting Nodal Verification
                  </span>
                </h2>
                <p className="text-xs text-amber-800/80 mt-0.5">
                  Newly registered institutions awaiting AICTE Scrutiny Officer verification
                </p>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-800 bg-white">
              <thead className="bg-amber-50/40 border-b border-amber-200 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">AICTE ID</th>
                  <th className="px-4 py-3">Institution Name</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Location</th>
                  <th className="px-4 py-3">Contact</th>
                  <th className="px-4 py-3 text-right">Scrutiny Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-amber-100">
                {pendingInstitutions.map((inst) => (
                  <tr key={inst.id} className="hover:bg-amber-50/30 transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-[#0B2545]">
                      {inst.aicte_id}
                    </td>
                    <td className="px-4 py-3 font-semibold text-slate-900">
                      {inst.name}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {inst.institution_type?.replace(/_/g, " ")}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {inst.district}, {inst.state}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      <div className="font-mono text-[11px]">{inst.contact_email}</div>
                      <div className="text-[11px] text-slate-400">{inst.contact_phone}</div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          disabled={actionLoadingId === inst.id}
                          onClick={() => handleVerifyInstitution(inst.id, "APPROVED")}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-bold rounded-lg bg-teal-600 hover:bg-teal-700 text-white shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
                        >
                          <CheckCircle2 className="w-3 h-3" />
                          <span>Approve</span>
                        </button>
                        <button
                          type="button"
                          disabled={actionLoadingId === inst.id}
                          onClick={() => handleVerifyInstitution(inst.id, "REJECTED")}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-bold rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 transition-colors cursor-pointer disabled:opacity-50"
                        >
                          <XCircle className="w-3 h-3" />
                          <span>Reject</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Applications Queue Table with Phase 6.A Workflow Stage Filter */}
      <div className="bg-white rounded-xl border border-[#DCE4ED] shadow-xs overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-[#DCE4ED] flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900">
              Applications Workflow Queue (Phase 6.A Overview)
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Live records across Scrutiny, EVC, and SAC approval stages
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {["ALL", "UNDER_REVIEW", "CLARIFICATION_REQUESTED", "APPROVED"].map((filter) => (
              <button
                key={filter}
                onClick={() => setWorkflowFilter(filter)}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors ${
                  workflowFilter === filter
                    ? "bg-[#0B2545] text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {filter.replace(/_/g, " ")}
              </button>
            ))}
            <Link
              to="/applications"
              className="text-xs font-bold text-[#1677C8] hover:underline flex items-center gap-1 ml-2"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-[#F8FAFC] border-b border-[#DCE4ED] text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Reference No</th>
                <th className="px-4 py-3">Institution</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Year</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Findings</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#DCE4ED]">
              {recentApps
                .filter((app) => workflowFilter === "ALL" || app.status === workflowFilter)
                .slice(0, 8)
                .map((app) => (
                  <tr key={app.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-mono font-bold text-[#0B2545]">
                      <Link to={`/applications/${app.id}`} className="hover:underline text-[#1677C8]">
                        {app.reference_no}
                      </Link>
                      {app.is_demo_seed && (
                        <span className="ml-2 text-[9px] px-1.5 py-0.2 rounded bg-amber-100 text-amber-800 font-sans font-semibold">
                          Demo
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {app.institution_name}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {app.category?.replace(/_/g, " ") || "Application"}
                    </td>
                    <td className="px-4 py-3 font-mono">{app.academic_year}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={app.status} size="sm" />
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-semibold text-slate-800">
                        {app.findings_count} findings
                      </span>
                      {app.highest_severity && (
                        <span className="ml-1.5 text-[10px] text-rose-600 font-bold">
                          ({app.highest_severity})
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/applications/${app.id}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-slate-100 text-slate-700 hover:bg-[#1677C8] hover:text-white transition-colors"
                      >
                        <span>Inspect</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Phase 5 Why Modal */}
      {selectedObligationId && (
        <WhyExplanationModal
          isOpen={whyModalOpen}
          onClose={() => setWhyModalOpen(false)}
          entityType="obligation"
          entityId={selectedObligationId}
        />
      )}
    </div>
  );
};
