import React, { useState, useEffect } from "react";
import {
  History,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  Lock,
  ArrowRight,
} from "lucide-react";
import { api } from "../services/api";

export const AuditTrailPage: React.FC = () => {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Integrity verification state
  const [verifying, setVerifying] = useState(false);
  const [integrityStatus, setIntegrityStatus] = useState<any | null>(null);

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditEvents({ limit: 100 });
      setEvents(data);
    } catch (err) {
      console.error("Failed to load audit events", err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChain = async () => {
    try {
      setVerifying(true);
      const res = await api.checkAuditIntegrity();
      setIntegrityStatus(res);
    } catch (err: any) {
      alert(`Integrity check failed: ${err.message}`);
    } finally {
      setVerifying(false);
    }
  };

  const filteredEvents = (events || []).filter((e) => {
    const matchAction = actionFilter === "ALL" || e.action === actionFilter;
    const matchSearch =
      (e.action || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (e.user_email && e.user_email.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (e.entity_type && e.entity_type.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (e.details && e.details.toLowerCase().includes(searchTerm.toLowerCase()));
    return matchAction && matchSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-[#0B2545] flex items-center gap-2">
              <History className="w-6 h-6 text-[#1677C8]" />
              Tamper-Evident SHA-256 Audit Trail
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 flex items-center gap-1 border border-emerald-200">
              <Lock className="w-3 h-3" /> Hash Chained
            </span>
          </div>
          <p className="text-sm text-slate-600">
            Immutable, cryptographically chained record of all regulatory actions, logins, rule evaluations, corrections, and scrutiny decisions.
          </p>
        </div>

        {/* Live Chain Verification Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleVerifyChain}
            disabled={verifying}
            className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-bold text-white bg-[#0B2545] hover:bg-[#123B63] rounded-lg shadow-sm transition-all"
          >
            <ShieldCheck className={`w-4 h-4 text-[#16A6C8] ${verifying ? "animate-spin" : ""}`} />
            {verifying ? "Verifying SHA-256 Chain..." : "Verify Audit Chain Integrity"}
          </button>
        </div>
      </div>

      {/* Integrity Verification Outcome Banner */}
      {integrityStatus && (
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 transition-all ${
            integrityStatus.status === "VALID"
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : "bg-rose-50 border-rose-200 text-rose-900"
          }`}
        >
          {integrityStatus.status === "VALID" ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          )}
          <div className="text-xs space-y-1">
            <div className="font-bold text-sm">
              Cryptographic Chain Status: {integrityStatus.status}
            </div>
            <div>
              {integrityStatus.message} (Verified {integrityStatus.verified_events_count} contiguous event blocks).
            </div>
            {integrityStatus.latest_hash && (
              <div className="font-mono text-[11px] text-slate-600 truncate mt-1">
                Latest Head Hash: {integrityStatus.latest_hash}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="relative flex-1 w-full md:max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by action, email, entity, or details..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1677C8]"
          />
        </div>
        <div className="flex items-center gap-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-[#1677C8]"
          >
            <option value="ALL">All Event Types</option>
            <option value="LOGIN">User Logins</option>
            <option value="VALIDATION_RUN">Rule Validations</option>
            <option value="VERIFICATION_ATTEMPT">Issuing Verifications</option>
            <option value="CLARIFICATION_REQUESTED">Clarification Requests</option>
            <option value="CORRECTION_SUBMITTED">Document Corrections</option>
            <option value="REVALIDATION_RUN">Selective Revalidations</option>
            <option value="DECISION_RECORDED">Officer Decisions</option>
          </select>
          <button
            onClick={loadEvents}
            disabled={loading}
            className="p-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-100"
            title="Refresh events"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#0B2545] text-white text-xs font-semibold uppercase tracking-wider">
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4">Actor</th>
              <th className="py-3 px-4">Action</th>
              <th className="py-3 px-4">Entity</th>
              <th className="py-3 px-4">Details</th>
              <th className="py-3 px-4 font-mono">SHA-256 Block Hash</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 text-xs font-sans">
            {loading ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  Loading cryptographic audit ledger...
                </td>
              </tr>
            ) : filteredEvents.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  No audit events found.
                </td>
              </tr>
            ) : (
              filteredEvents.map((evt) => (
                <tr key={evt.id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                    {new Date(evt.timestamp).toLocaleString()}
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-900">
                    <div>{evt.user_email || "SYSTEM"}</div>
                    <div className="text-[10px] text-slate-400">IP: {evt.ip_address || "127.0.0.1"}</div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                      {evt.action}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-700">
                    {evt.entity_type ? `${evt.entity_type} #${evt.entity_id || ""}` : "—"}
                  </td>
                  <td className="py-3 px-4 max-w-xs text-slate-600 truncate" title={evt.details}>
                    {evt.details}
                  </td>
                  <td className="py-3 px-4 font-mono text-[10px] text-slate-500">
                    <div className="truncate w-32" title={evt.entry_hash}>
                      {evt.entry_hash ? `${evt.entry_hash.slice(0, 16)}...` : "—"}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

