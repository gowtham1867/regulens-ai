import React, { useState, useEffect } from "react";
import { Network, RefreshCw, Building, ShieldCheck } from "lucide-react";
import { api } from "../services/api";
import { TrustGraphViewer } from "../components/trustgraph/TrustGraphViewer";
import type { TrustGraphData, Application } from "../types";

export const TrustGraphExplorer: React.FC = () => {
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);
  const [graphData, setGraphData] = useState<TrustGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  useEffect(() => {
    loadApplications();
  }, []);

  useEffect(() => {
    if (selectedAppId) {
      loadGraph(selectedAppId);
    }
  }, [selectedAppId]);

  const loadApplications = async () => {
    try {
      setLoading(true);
      const data = await api.getApplications();
      setApplications(data);
      if (data.length > 0) {
        setSelectedAppId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to load applications:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadGraph = async (appId: number) => {
    setRefreshing(true);
    try {
      const data = await api.getTrustGraph(appId);
      setGraphData(data);
    } catch (err) {
      console.error("Failed to load TrustGraph:", err);
    } finally {
      setRefreshing(false);
    }
  };

  const selectedApp = applications.find((a) => a.id === selectedAppId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-2xl border border-[#DCE4ED] shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-black text-[#0B2545] flex items-center gap-2">
              <Network className="w-6 h-6 text-[#1677C8]" />
              TrustGraph Evidence Registry & Provenance Topology
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#16A6C8]/10 text-[#0B2545] border border-[#16A6C8]/30">
              Stage 10 Architecture
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl">
            Cryptographic 5-tier traceability topology mapping declarations, raw supporting documents, PyMuPDF OCR claims, issuer verifications, and scrutiny decisions.
          </p>
        </div>

        {/* Application Selector */}
        <div className="flex items-center gap-2 self-start md:self-auto">
          <label className="text-xs font-bold text-slate-700 shrink-0">Application:</label>
          <select
            value={selectedAppId || ""}
            onChange={(e) => setSelectedAppId(parseInt(e.target.value, 10))}
            className="text-xs font-bold bg-slate-50 border border-[#DCE4ED] rounded-xl px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#1677C8]"
          >
            {applications.map((app) => (
              <option key={app.id} value={app.id}>
                {app.reference_no} — {(app.institution_name || "Institution").substring(0, 30)}
              </option>
            ))}
          </select>
          <button
            onClick={() => selectedAppId && loadGraph(selectedAppId)}
            disabled={refreshing}
            className="p-2 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-600 disabled:opacity-50"
            title="Refresh Graph"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Selected Application Context Banner */}
      {selectedApp && (
        <div className="bg-[#0B2545] text-white p-4 rounded-xl flex flex-wrap items-center justify-between gap-4 text-xs shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-800/80">
              <Building className="w-4 h-4 text-cyan-300" />
            </div>
            <div>
              <div className="font-bold text-sm text-white">{selectedApp.institution_name}</div>
              <div className="text-[11px] text-slate-300 flex items-center gap-3 mt-0.5">
                <span>Ref: <b className="font-mono text-cyan-300">{selectedApp.reference_no}</b></span>
                <span>•</span>
                <span>Year: <b className="font-mono text-white">{selectedApp.academic_year}</b></span>
                <span>•</span>
                <span>Category: <b>{selectedApp.category.replace(/_/g, " ")}</b></span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4 text-[11px]">
            <div>
              <span className="text-slate-400">Declared Land: </span>
              <b className="text-white">{selectedApp.declared_land_acres || "N/A"} Acres</b>
            </div>
            <div>
              <span className="text-slate-400">Intake: </span>
              <b className="text-white">{selectedApp.declared_intake || "N/A"} Seats</b>
            </div>
            <div className="px-2.5 py-1 rounded bg-blue-900/80 border border-blue-700/60 font-bold uppercase text-[10px]">
              {selectedApp.status}
            </div>
          </div>
        </div>
      )}

      {/* Render 5-Tier Dark Canvas & Sub-tabs */}
      <TrustGraphViewer data={graphData} loading={loading || refreshing} />
    </div>
  );
};
