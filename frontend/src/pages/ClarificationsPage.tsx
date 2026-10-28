import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  HelpCircle,
  Clock,
  CheckCircle2,
  AlertCircle,
  Building,
  ArrowRight,
  Filter,
  RefreshCw,
  Search,
} from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { StatusBadge } from "../components/common/StatusBadge";

export const ClarificationsPage: React.FC = () => {
  const { user } = useAuth();
  const [applications, setApplications] = useState<any[]>([]);
  const [clarificationsMap, setClarificationsMap] = useState<Record<number, any[]>>({});
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const apps = await api.getApplications();
      setApplications(apps);

      // Fetch clarifications for each application
      const map: Record<number, any[]> = {};
      for (const app of apps) {
        try {
          const reqs = await api.getClarifications(app.id);
          if (reqs && reqs.length > 0) {
            map[app.id] = reqs;
          }
        } catch {
          // ignore individual failures
        }
      }
      setClarificationsMap(map);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Flatten all clarifications with application context
  const allClarifications = Object.entries(clarificationsMap).flatMap(([appId, reqs]) => {
    const parentApp = applications.find((a) => a.id === Number(appId));
    return reqs.map((r) => ({
      ...r,
      appId: Number(appId),
      appRef: parentApp?.reference_no || `App #${appId}`,
      appName: parentApp?.title || "Application",
      institutionName: parentApp?.institution_name || "Institution",
    }));
  });

  const filtered = allClarifications.filter((c) => {
    const matchStatus = filterStatus === "ALL" || c.status === filterStatus;
    const matchSearch =
      (c.appRef || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.institutionName || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.subject || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (c.requested_information || "").toLowerCase().includes(searchTerm.toLowerCase());
    return matchStatus && matchSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#0B2545] flex items-center gap-2 mb-1">
            <HelpCircle className="w-6 h-6 text-[#1677C8]" />
            Regulatory Clarification Requests
          </h1>
          <p className="text-sm text-slate-600">
            Track communication loops between scrutiny officers and applicant institutions for deficient documents or shortfall rectifications.
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-300 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh Requests
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="relative flex-1 w-full md:max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by application, institution, or notes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1677C8]"
          />
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-[#1677C8]"
          >
            <option value="ALL">All Statuses</option>
            <option value="PENDING">Pending Response</option>
            <option value="RESOLVED">Resolved / Revalidated</option>
          </select>
        </div>
      </div>

      {/* Clarification Cards */}
      <div className="space-y-4">
        {loading ? (
          <div className="bg-white p-12 text-center text-slate-500 rounded-xl border border-slate-200">
            Loading clarification records...
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-white p-12 text-center text-slate-500 rounded-xl border border-slate-200">
            No clarification requests match the selected criteria.
          </div>
        ) : (
          filtered.map((item) => (
            <div
              key={item.id}
              className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:border-[#1677C8] transition-all"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs font-bold text-[#1677C8] bg-blue-50 px-2.5 py-1 rounded border border-blue-100">
                    {item.appRef}
                  </span>
                  <StatusBadge status={item.status} />
                </div>
                <div className="text-xs text-slate-500 flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  Requested on {new Date(item.created_at).toLocaleDateString()}
                  {item.deadline_date && (
                    <span className="text-rose-600 font-semibold ml-2">
                      Deadline: {item.deadline_date}
                    </span>
                  )}
                </div>
              </div>

              <div className="mb-3">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                  <Building className="w-4 h-4 text-slate-600" />
                  {item.institutionName}
                </h3>
                <div className="font-semibold text-slate-800 text-sm mt-1">
                  Subject: {item.subject}
                </div>
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5 mb-4 text-xs text-slate-700 space-y-2">
                <div>
                  <div className="font-semibold text-slate-900 mb-0.5">
                    Officer Inquired Information (Issued by {item.officer_name}):
                  </div>
                  <p className="leading-relaxed whitespace-pre-wrap text-slate-800">{item.requested_information}</p>
                </div>

                {item.instructions_for_correction && (
                  <div className="pt-2 border-t border-slate-200">
                    <div className="font-semibold text-indigo-900 mb-0.5">Correction Instructions:</div>
                    <p className="text-slate-800 leading-relaxed">{item.instructions_for_correction}</p>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                <div className="text-xs text-slate-500">
                  {item.status === "RESOLVED" || item.status === "RESPONDED" ? (
                    <span className="text-emerald-700 font-medium">
                      ✓ Corrected Evidence Processed
                    </span>
                  ) : (
                    <span className="text-amber-700 font-medium">
                      ⏳ Awaiting Institutional Evidence Upload
                    </span>
                  )}
                </div>
                <Link
                  to={`/applications/${item.appId}`}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#1677C8] hover:text-[#0B2545] transition-colors"
                >
                  Open Application Scrutiny <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

