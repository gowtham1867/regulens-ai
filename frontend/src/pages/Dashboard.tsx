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
  Building2
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { StatusBadge } from "../components/common/StatusBadge";
import type { Application } from "../types";

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const isOfficerOrAdmin = user?.role === "AICTE_OFFICER" || user?.role === "ADMINISTRATOR";

  const [summary, setSummary] = useState<any>(null);
  const [recentApps, setRecentApps] = useState<Application[]>([]);
  const [pendingInstitutions, setPendingInstitutions] = useState<any[]>([]);
  const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [sumData, appsData] = await Promise.all([
        api.getDashboardSummary(),
        api.getApplications(),
      ]);
      setSummary(sumData);
      setRecentApps(Array.isArray(appsData) ? appsData.slice(0, 5) : []);

      if (isOfficerOrAdmin) {
        try {
          const pending = await api.getPendingInstitutions();
          setPendingInstitutions(pending || []);
        } catch (e) {
          console.warn("Failed to load pending institutions:", e);
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

  const metricCards = [
    {
      title: "Total Applications",
      value: summary?.total_applications ?? 0,
      icon: FileText,
      color: "border-[#1677C8] text-[#1677C8]",
      bg: "bg-blue-50/50",
    },
    {
      title: "Under Scrutiny / Review",
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
      title: "Awaiting Clarification",
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
      title: "Approved Scrutiny",
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
            {user?.role === "INSTITUTION_USER" ? "Institution Scrutiny Portal" : "AICTE Scrutiny Officer Workspace"}
          </div>
          <h1 className="text-xl md:text-2xl font-black mt-1">
            Welcome back, {user?.full_name}
          </h1>
          <p className="text-xs text-slate-300 mt-1 max-w-xl leading-relaxed">
            {user?.role === "INSTITUTION_USER"
              ? `Manage applications, upload verified supporting evidence, and track clarification requests for ${user.institution_name}.`
              : "Scrutinize technical institute submissions with automated OCR extraction, deterministic regulatory rule verification, and TrustGraph evidence traceability."}
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          {user?.role === "INSTITUTION_USER" ? (
            <Link
              to="/applications/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#1677C8] hover:bg-[#1264a8] text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
            >
              <PlusCircle className="w-4 h-4" />
              <span>New Application</span>
            </Link>
          ) : (
            <Link
              to="/evaluation"
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#1677C8] hover:bg-[#1264a8] text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
            >
              <Activity className="w-4 h-4" />
              <span>Run Benchmark Suite</span>
            </Link>
          )}
          <Link
            to="/applications"
            className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-xs font-bold transition-colors border border-white/20"
          >
            <span>View Queue</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Operational Metrics Grid (Calculated from DB Records - Rule 2) */}
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

      {/* Pending Institution Scrutiny & Approval (Officer Gateway) */}
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

      {/* Applications Table */}
      <div className="bg-white rounded-xl border border-[#DCE4ED] shadow-xs overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-[#DCE4ED] flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Recent Applications in Scrutiny</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Live records from persistent regulatory scrutiny database
            </p>
          </div>
          <Link
            to="/applications"
            className="text-xs font-bold text-[#1677C8] hover:underline flex items-center gap-1"
          >
            <span>View All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
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
              {recentApps.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    No applications currently recorded.
                  </td>
                </tr>
              ) : (
                recentApps.map((app) => (
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
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

