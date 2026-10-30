import React, { useState, useEffect } from "react";
import {
  BarChart3,
  Download,
  FileSpreadsheet,
  CheckCircle2,
  Clock,
  ShieldCheck,
  AlertTriangle,
  Layers,
  Users,
  Calendar,
  Lock,
  ChevronRight
} from "lucide-react";
import api from "../services/api";

export const ComplianceReportsPage: React.FC = () => {
  const [reportsList, setReportsList] = useState<any[]>([]);
  const [selectedKey, setSelectedKey] = useState<string>("pendency_ageing");
  const [reportData, setReportData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [downloading, setDownloading] = useState<boolean>(false);

  useEffect(() => {
    api.get("/compliance-reports").then((res: any) => {
      setReportsList(res.data);
    });
  }, []);

  const fetchReport = async (key: string) => {
    try {
      setLoading(true);
      const res = await api.get(`/compliance-reports/${key}`);
      setReportData(res.data);
    } catch (err) {
      console.error("Failed to load report:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedKey) {
      fetchReport(selectedKey);
    }
  }, [selectedKey]);

  const handleDownloadCsv = async () => {
    try {
      setDownloading(true);
      const response = await api.get(`/compliance-reports/${selectedKey}/export.csv`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "text/csv;charset=utf-8;" }));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `regulens_${selectedKey}_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (err) {
      alert("Failed to export report CSV.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-[#1677C8]/10 text-[#1677C8]">
              Phase 13
            </span>
            <span className="text-xs text-slate-500 font-medium">Statutory Oversight & Performance Intelligence</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-[#1677C8]" />
            Regulatory Compliance & Pendency Reports Suite
          </h1>
          <p className="text-sm text-slate-600 mt-1 max-w-3xl">
            11 dedicated real-time performance and pendency audit reports with automated CSV exports for AICTE executive oversight.
          </p>
        </div>

        <button
          onClick={handleDownloadCsv}
          disabled={downloading || loading}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[#1677C8] hover:bg-[#123B63] text-white text-xs font-bold shadow-sm transition-all disabled:opacity-50"
        >
          <Download className="w-4 h-4" />
          {downloading ? "Exporting CSV..." : "Export Official CSV"}
        </button>
      </div>

      {/* Grid Layout: Left Reports Navigation, Right Report Details */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Reports Navigation Sidebar */}
        <div className="lg:col-span-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-3 space-y-1">
          <div className="px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Official Reports (11)
          </div>
          {reportsList.map((rep) => {
            const isSelected = selectedKey === rep.key;
            return (
              <button
                key={rep.key}
                onClick={() => setSelectedKey(rep.key)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center justify-between transition-all ${
                  isSelected
                    ? "bg-[#0B2545] text-white shadow-sm font-bold"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                <span className="truncate pr-2">{rep.title}</span>
                <ChevronRight className={`w-3.5 h-3.5 shrink-0 ${isSelected ? "text-[#16A6C8]" : "text-slate-400"}`} />
              </button>
            );
          })}
        </div>

        {/* Report Display Area */}
        <div className="lg:col-span-3 space-y-6">
          {loading ? (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500 font-medium">
              Generating real-time report analysis...
            </div>
          ) : !reportData ? (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
              Select a report from the menu to inspect data.
            </div>
          ) : (
            <>
              {/* Report Title & Summary Cards */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <h2 className="text-lg font-bold text-slate-900">{reportData.title}</h2>
                  <span className="text-xs text-slate-500">
                    Generated: {new Date().toLocaleTimeString()} UTC
                  </span>
                </div>

                {/* Summary Metrics */}
                {reportData.summary && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {Object.entries(reportData.summary).map(([k, v]: [string, any], i: number) => {
                      if (typeof v === "object") return null;
                      return (
                        <div key={i} className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                          <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                            {k.replace(/_/g, " ")}
                          </span>
                          <span className="text-xl font-black text-slate-900 mt-1 block">
                            {String(v)}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Data Table Preview */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-3.5 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
                  <div className="text-xs font-bold text-slate-700">
                    Data Records ({reportData.rows?.length || 0})
                  </div>
                  <button
                    onClick={handleDownloadCsv}
                    className="text-xs font-bold text-[#1677C8] hover:underline flex items-center gap-1"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download CSV
                  </button>
                </div>

                <div className="overflow-x-auto max-h-[500px]">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead className="sticky top-0 bg-slate-100 text-slate-700 font-bold border-b border-slate-200 z-10">
                      <tr>
                        {reportData.headers?.map((h: string) => (
                          <th key={h} className="py-2.5 px-3.5 capitalize">
                            {h.replace(/_/g, " ")}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-800">
                      {reportData.rows?.length === 0 ? (
                        <tr>
                          <td colSpan={reportData.headers?.length || 1} className="py-8 text-center text-slate-500">
                            No records found.
                          </td>
                        </tr>
                      ) : (
                        reportData.rows?.map((row: any, rIdx: number) => (
                          <tr key={rIdx} className="hover:bg-slate-50/80 transition-colors">
                            {reportData.headers?.map((h: string) => (
                              <td key={h} className="py-2.5 px-3.5 max-w-xs truncate font-medium">
                                {String(row[h] !== undefined ? row[h] : "")}
                              </td>
                            ))}
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
