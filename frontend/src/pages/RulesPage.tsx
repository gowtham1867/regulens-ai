import React, { useState, useEffect } from "react";
import {
  BookOpen,
  CheckCircle,
  ToggleLeft,
  ToggleRight,
  ShieldAlert,
  Info,
  RefreshCw,
  Search,
} from "lucide-react";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { StatusBadge } from "../components/common/StatusBadge";

export const RulesPage: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMINISTRATOR";

  const [rules, setRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [togglingId, setTogglingId] = useState<number | null>(null);

  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    try {
      setLoading(true);
      const data = await api.getRules();
      setRules(data);
    } catch (err: any) {
      setError(err.message || "Failed to load regulatory rules");
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (ruleId: number) => {
    if (!isAdmin) return;
    try {
      setTogglingId(ruleId);
      await api.toggleRule(ruleId);
      await loadRules();
    } catch (err: any) {
      alert(`Error toggling rule: ${err.message}`);
    } finally {
      setTogglingId(null);
    }
  };

  const filteredRules = (rules || []).filter(
    (r) =>
      (r.rule_code || "").toLowerCase().includes(search.toLowerCase()) ||
      (r.title || "").toLowerCase().includes(search.toLowerCase()) ||
      (r.category || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[#0B2545] flex items-center gap-2 mb-1">
            <BookOpen className="w-6 h-6 text-[#1677C8]" />
            Regulatory Rules & Checklist Standards
          </h1>
          <p className="text-sm text-slate-600">
            Versioned AICTE compliance rules enforced deterministically across submitted institution applications.
          </p>
        </div>
        <button
          onClick={loadRules}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-300 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh Rules
        </button>
      </div>

      {/* Handbook Citation Banner */}
      <div className="bg-blue-50 border border-blue-200 p-4 rounded-xl flex items-start gap-3">
        <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div className="text-xs text-blue-900 leading-relaxed">
          <strong>Statutory Governance:</strong> Rules follow the AICTE Approval Process Handbook (APH 2024–27). Evaluation results link directly to statutory norm thresholds. Administrators may toggle active rules to adjust compliance requirements for specific scrutiny cycles.
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search rules by code, title, or category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1677C8]"
          />
        </div>
        <div className="text-xs text-slate-500 font-medium">
          Showing {filteredRules.length} of {rules.length} rules
        </div>
      </div>

      {/* Rules Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#0B2545] text-white text-xs font-semibold uppercase tracking-wider">
              <th className="py-3 px-4">Rule Code & Version</th>
              <th className="py-3 px-4">Title & Statutory Scope</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4">Severity</th>
              <th className="py-3 px-4">Status</th>
              {isAdmin && <th className="py-3 px-4 text-right">Admin Action</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 text-xs">
            {loading ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  Loading regulatory rules...
                </td>
              </tr>
            ) : filteredRules.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500">
                  No matching rules found.
                </td>
              </tr>
            ) : (
              filteredRules.map((rule) => (
                <tr key={rule.id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3.5 px-4 font-mono font-bold text-slate-900">
                    <div>{rule.rule_code}</div>
                    <div className="text-[10px] text-slate-500 font-normal">v{rule.version}</div>
                  </td>
                  <td className="py-3.5 px-4 max-w-md">
                    <div className="font-semibold text-slate-900 mb-0.5">{rule.title}</div>
                    <div className="text-slate-600 leading-snug">{rule.description}</div>
                  </td>
                  <td className="py-3.5 px-4 font-medium text-slate-700">
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                      {rule.category}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <StatusBadge status={rule.severity} />
                  </td>
                  <td className="py-3.5 px-4">
                    {rule.is_active ? (
                      <span className="inline-flex items-center gap-1 font-semibold text-emerald-700">
                        <CheckCircle className="w-3.5 h-3.5" /> Active
                      </span>
                    ) : (
                      <span className="font-semibold text-slate-400">Inactive</span>
                    )}
                  </td>
                  {isAdmin && (
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleToggle(rule.id)}
                        disabled={togglingId === rule.id}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                          rule.is_active
                            ? "bg-amber-100 text-amber-900 hover:bg-amber-200"
                            : "bg-emerald-100 text-emerald-900 hover:bg-emerald-200"
                        }`}
                      >
                        {rule.is_active ? (
                          <>
                            <ToggleRight className="w-4 h-4 text-amber-700" /> Deactivate
                          </>
                        ) : (
                          <>
                            <ToggleLeft className="w-4 h-4 text-slate-500" /> Activate
                          </>
                        )}
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

