import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Building,
  RefreshCw,
  Search,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Info,
} from "lucide-react";
import { api } from "../services/api";
import { SimulatedBadge } from "../components/common/SimulatedBadge";
import { StatusBadge } from "../components/common/StatusBadge";

export const VerificationPage: React.FC = () => {
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Quick lookup state
  const [selectedSource, setSelectedSource] = useState<string>("");
  const [recordNumber, setRecordNumber] = useState<string>("");
  const [lookupResult, setLookupResult] = useState<any | null>(null);
  const [lookupLoading, setLookupLoading] = useState(false);

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    try {
      setLoading(true);
      const data = await api.getVerificationSources();
      setSources(data);
      if (data.length > 0 && !selectedSource) {
        setSelectedSource(data[0].source_code);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load verification sources");
    } finally {
      setLoading(false);
    }
  };

  const handleTestLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recordNumber) return;
    setLookupLoading(true);
    setLookupResult(null);

    // Demonstration synthetic query for test console
    setTimeout(() => {
      if (recordNumber.toUpperCase().includes("NOC-2024-8849")) {
        setLookupResult({
          status: "VERIFIED",
          institution_name: "Apex Institute of Technology & Engineering",
          issuer: "State Directorate of Fire & Emergency Services",
          issued_date: "2024-05-10",
          valid_until: "2026-05-09",
          badge: "SIMULATED VERIFICATION",
          confidence: 0.99,
          records_match: true,
          details: "Active regulatory compliance certificate verified in mock state registry."
        });
      } else if (recordNumber.toUpperCase().includes("NOC-2021-1049")) {
        setLookupResult({
          status: "EXPIRED_IN_REGISTRY",
          institution_name: "Sunrise Polymers Warehouse / Zenith College",
          issuer: "State Directorate of Fire & Emergency Services",
          issued_date: "2021-01-16",
          valid_until: "2023-01-15",
          badge: "SIMULATED VERIFICATION",
          confidence: 0.99,
          records_match: false,
          details: "Record found in registry but validity expired on 15-Jan-2023. Violates current compliance norms."
        });
      } else if (recordNumber.toUpperCase().includes("DEED-2018-99214")) {
        setLookupResult({
          status: "VERIFIED",
          institution_name: "Apex Educational Foundation",
          issuer: "Department of Revenue & Land Administration",
          land_area_acres: 8.5,
          badge: "SIMULATED VERIFICATION",
          confidence: 0.98,
          records_match: true,
          details: "Registered clear title deed verified in mock state land revenue database."
        });
      } else {
        setLookupResult({
          status: "RECORD_NOT_FOUND",
          issuer: sources.find(s => s.source_code === selectedSource)?.name || "External Registry",
          badge: "SIMULATED VERIFICATION",
          confidence: 0.0,
          records_match: false,
          details: `Identifier '${recordNumber}' could not be located in simulated issuing registry database.`
        });
      }
      setLookupLoading(false);
    }, 600);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-[#0B2545]">
              Issuing Authority Verification Hub
            </h1>
            <SimulatedBadge />
          </div>
          <p className="text-sm text-slate-600">
            Automated verification adapters for statutory document authorities with deterministic audit caching and honest simulation labelling.
          </p>
        </div>
        <button
          onClick={loadSources}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg border border-slate-300 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh Adapters
        </button>
      </div>

      {/* Honest AICTE Disclaimer Banner */}
      <div className="bg-amber-50 border border-amber-200 p-4 rounded-xl flex items-start gap-3">
        <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs text-amber-800 leading-relaxed">
          <strong>Transparency Notice:</strong> In accordance with SIH prototype specifications, external issuing authorities (State Fire Services, Land Revenue Departments, and University Affiliation Portals) are accessed via structured deterministic adapters. Live production deployment will connect via National Data Governance Sandbox APIs.
        </div>
      </div>

      {/* Grid of Configured Adapters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-3 py-12 text-center text-slate-500">Loading adapters...</div>
        ) : (
          sources.map((src) => (
            <div
              key={src.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between hover:border-[#1677C8] transition-all"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-blue-50 text-[#1677C8] border border-blue-100">
                    {src.source_code}
                  </span>
                  <SimulatedBadge />
                </div>
                <h3 className="text-base font-bold text-[#0B2545] mb-1.5 flex items-center gap-2">
                  <Building className="w-4 h-4 text-[#1677C8]" />
                  {src.name}
                </h3>
                <p className="text-xs text-slate-600 mb-3 leading-relaxed">
                  {src.description}
                </p>
                <div className="space-y-1.5 text-xs text-slate-500 border-t border-slate-100 pt-3">
                  <div>
                    <span className="font-medium text-slate-700">Authority Type:</span> {src.authority_type}
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Protocol:</span> REST JSON / SHA-256 Checksum
                  </div>
                  <div>
                    <span className="font-medium text-slate-700">Status:</span>{" "}
                    <span className="text-emerald-600 font-semibold">ONLINE (Adapter Ready)</span>
                  </div>
                </div>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-slate-400">Cache TTL: 24 Hours</span>
                <button
                  onClick={() => {
                    setSelectedSource(src.source_code);
                    if (src.source_code === "STATE_FIRE_SERVICES_PORTAL") setRecordNumber("NOC-2024-8849");
                    else if (src.source_code === "STATE_REVENUE_LAND_REGISTRY") setRecordNumber("DEED-2018-99214");
                    else setRecordNumber("AFF-AKTU-2024-512");
                  }}
                  className="text-xs font-semibold text-[#1677C8] hover:underline flex items-center gap-1"
                >
                  Test Query <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Interactive Adapter Test Console */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h2 className="text-lg font-bold text-[#0B2545] mb-2 flex items-center gap-2">
          <Search className="w-5 h-5 text-[#1677C8]" />
          Interactive Adapter Query Console
        </h2>
        <p className="text-xs text-slate-600 mb-4">
          Test issuing authority lookups against deterministic demo datasets. Supports sample queries like <code>NOC-2024-8849</code> (Valid), <code>NOC-2021-1049</code> (Expired), or <code>DEED-2018-99214</code>.
        </p>

        <form onSubmit={handleTestLookup} className="grid grid-cols-1 md:grid-cols-12 gap-3 mb-6">
          <div className="md:col-span-4">
            <label className="block text-xs font-medium text-slate-700 mb-1">Select Authority Source</label>
            <select
              value={selectedSource}
              onChange={(e) => setSelectedSource(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1677C8] bg-white"
            >
              {sources.map((s) => (
                <option key={s.id} value={s.source_code}>
                  {s.name} ({s.source_code})
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-6">
            <label className="block text-xs font-medium text-slate-700 mb-1">Registration / Certificate Number</label>
            <input
              type="text"
              value={recordNumber}
              onChange={(e) => setRecordNumber(e.target.value)}
              placeholder="e.g. NOC-2024-8849, DEED-2018-99214"
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1677C8]"
            />
          </div>
          <div className="md:col-span-2 flex items-end">
            <button
              type="submit"
              disabled={lookupLoading || !recordNumber}
              className="w-full py-2 px-4 text-sm font-semibold text-white bg-[#1677C8] hover:bg-[#123B63] rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {lookupLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : "Query Adapter"}
            </button>
          </div>
        </form>

        {/* Query Result Card */}
        {lookupResult && (
          <div className="border border-slate-200 rounded-xl p-5 bg-slate-50">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase text-slate-500">Query Outcome:</span>
                <StatusBadge status={lookupResult.status} />
              </div>
              <SimulatedBadge />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="space-y-1">
                <div className="text-slate-500">Target Authority:</div>
                <div className="font-semibold text-slate-800">{lookupResult.issuer}</div>
              </div>
              {lookupResult.institution_name && (
                <div className="space-y-1">
                  <div className="text-slate-500">Registered Entity:</div>
                  <div className="font-semibold text-slate-800">{lookupResult.institution_name}</div>
                </div>
              )}
              {lookupResult.valid_until && (
                <div className="space-y-1">
                  <div className="text-slate-500">Validity Horizon:</div>
                  <div className="font-semibold text-slate-800">Until {lookupResult.valid_until}</div>
                </div>
              )}
              {lookupResult.land_area_acres && (
                <div className="space-y-1">
                  <div className="text-slate-500">Registered Acreage:</div>
                  <div className="font-semibold text-slate-800">{lookupResult.land_area_acres} Acres</div>
                </div>
              )}
            </div>

            <div className="mt-4 pt-3 border-t border-slate-200 text-xs text-slate-700 bg-white p-3 rounded-lg border border-slate-200">
              <span className="font-semibold text-slate-900">Adapter Evidence Note: </span>
              {lookupResult.details}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
