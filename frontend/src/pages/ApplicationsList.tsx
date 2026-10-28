import React, { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PlusCircle, Search, Filter, ArrowRight, RefreshCw, FileText, Download } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { StatusBadge } from "../components/common/StatusBadge";
import type { Application } from "../types";

export const ApplicationsList: React.FC = () => {
  const { user } = useAuth();
  const isOfficerOrAdmin = user?.role === "AICTE_OFFICER" || user?.role === "ADMINISTRATOR";
  const [searchParams, setSearchParams] = useSearchParams();

  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [exportingCsv, setExportingCsv] = useState(false);

  const handleExportQueueCsv = async () => {
    setExportingCsv(true);
    try {
      const { blob, filename } = await api.exportApplicationsQueueCsv({
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        search: searchTerm || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || `regulens_applications_${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(err.message || "Failed to export applications CSV");
    } finally {
      setExportingCsv(false);
    }
  };

  const statusFilter = searchParams.get("status") || "";
  const categoryFilter = searchParams.get("category") || "";
  const searchTerm = searchParams.get("search") || "";

  useEffect(() => {
    loadApplications();
  }, [searchParams]);

  const loadApplications = async () => {
    setLoading(true);
    try {
      const data = await api.getApplications({
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        search: searchTerm || undefined,
      });
      setApplications(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key: string, value: string) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Applications Scrutiny Queue</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Comprehensive listing of institutional applications under regulatory review
          </p>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-auto">
          <button
            onClick={handleExportQueueCsv}
            disabled={exportingCsv || loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-[#DCE4ED] hover:bg-slate-50 text-[#0B2545] rounded-lg text-xs font-bold transition-colors shadow-xs cursor-pointer disabled:opacity-50"
            title="Export filtered application queue to CSV"
          >
            <Download className={`w-3.5 h-3.5 text-[#1677C8] ${exportingCsv ? "animate-bounce" : ""}`} />
            <span>{exportingCsv ? "Exporting CSV..." : "Export CSV"}</span>
          </button>

          {user?.role === "INSTITUTION_USER" && (
            <Link
              to="/applications/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#0B2545] hover:bg-[#123B63] text-white rounded-lg text-xs font-bold transition-colors shadow-sm"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Submit Application</span>
            </Link>
          )}
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-[#DCE4ED] shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="w-full md:w-80 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => handleFilterChange("search", e.target.value)}
            placeholder="Search reference, institution, AICTE ID..."
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-[#F4F7FB] border border-[#DCE4ED] rounded-lg focus:outline-none focus:ring-1 focus:ring-[#1677C8] focus:bg-white"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2.5 w-full md:w-auto">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => handleFilterChange("status", e.target.value)}
            className="text-xs bg-[#F4F7FB] border border-[#DCE4ED] rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
          >
            <option value="">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="CLARIFICATION_REQUESTED">Clarification Requested</option>
            <option value="CORRECTION_SUBMITTED">Correction Submitted</option>
            <option value="READY_FOR_DECISION">Ready for Decision</option>
            <option value="APPROVED">Approved</option>
            <option value="RETURNED">Returned</option>
            <option value="REJECTED">Rejected</option>
          </select>

          {/* Category Filter */}
          <select
            value={categoryFilter}
            onChange={(e) => handleFilterChange("category", e.target.value)}
            className="text-xs bg-[#F4F7FB] border border-[#DCE4ED] rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-[#1677C8]"
          >
            <option value="">All Categories</option>
            <option value="EXTENSION_OF_APPROVAL">Extension of Approval (EoA)</option>
            <option value="NEW_INSTITUTION">New Technical Institution</option>
            <option value="INCREASE_IN_INTAKE">Increase in Intake</option>
          </select>

          <button
            onClick={loadApplications}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg border border-[#DCE4ED]"
            title="Refresh List"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Applications Table */}
      <div className="bg-white rounded-xl border border-[#DCE4ED] shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-[#F8FAFC] border-b border-[#DCE4ED] text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Reference No</th>
                <th className="px-4 py-3">Institution Name</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Deficiencies / Findings</th>
                <th className="px-4 py-3">Assigned Officer</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#DCE4ED]">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    Loading applications...
                  </td>
                </tr>
              ) : applications.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    No matching applications found.
                  </td>
                </tr>
              ) : (
                applications.map((app) => (
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
                    <td className="px-4 py-3 text-slate-600">
                      {app.assigned_officer_name || "Unassigned"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/applications/${app.id}`}
                        className="inline-flex items-center gap-1 px-3 py-1 text-xs font-semibold rounded bg-[#0B2545] text-white hover:bg-[#123B63] transition-colors"
                      >
                        <span>{isOfficerOrAdmin ? "Review & Action" : "Workspace"}</span>
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

