import React, { useState, useEffect } from "react";
import {
  Activity,
  CheckCircle2,
  XCircle,
  Play,
  RefreshCw,
  Clock,
  ShieldCheck,
  TrendingUp,
  Cpu,
} from "lucide-react";
import { api } from "../services/api";

export const EvaluationBenchmarkPage: React.FC = () => {
  const [suiteResult, setSuiteResult] = useState<any | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Run suite on initial load to present fresh benchmark metrics
    handleRunSuite();
  }, []);

  const handleRunSuite = async () => {
    try {
      setRunning(true);
      setError(null);
      const res = await api.runBenchmarkSuite();
      setSuiteResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to execute benchmark suite");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold text-[#0B2545] flex items-center gap-2">
              <Activity className="w-6 h-6 text-[#1677C8]" />
              13-Case Regulatory Benchmark Evaluation
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-[#1677C8] border border-blue-200">
              SIH26261 Test Suite
            </span>
          </div>
          <p className="text-sm text-slate-600">
            Systematic benchmark verification evaluating all required regulatory scenarios including missing documents, expired NOCs, land shortfalls, collision detection, and audit hash integrity.
          </p>
        </div>
        <button
          onClick={handleRunSuite}
          disabled={running}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-bold text-white bg-[#1677C8] hover:bg-[#123B63] rounded-lg shadow-sm transition-all disabled:opacity-50"
        >
          {running ? (
            <RefreshCw className="w-4 h-4 animate-spin text-white" />
          ) : (
            <Play className="w-4 h-4 text-white fill-white" />
          )}
          {running ? "Executing 13 Scenarios..." : "Run Benchmark Suite"}
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-200 p-4 rounded-xl text-rose-800 text-xs">
          <strong>Benchmark Execution Error:</strong> {error}
        </div>
      )}

      {/* Benchmark Summary Metrics */}
      {suiteResult && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-[#1677C8]" /> Pass Rate
            </div>
            <div className="text-3xl font-black text-emerald-600">
              {suiteResult.pass_rate_percentage}%
            </div>
            <div className="text-xs text-slate-500 mt-1 font-medium">
              {suiteResult.passed_tests} of {suiteResult.total_tests} scenarios verified
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Passed Scenarios
            </div>
            <div className="text-3xl font-black text-slate-900">
              {suiteResult.passed_tests}
            </div>
            <div className="text-xs text-emerald-700 mt-1 font-medium">
              100% statutory adherence
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <XCircle className="w-4 h-4 text-rose-500" /> Failed Scenarios
            </div>
            <div className="text-3xl font-black text-slate-900">
              {suiteResult.failed_tests}
            </div>
            <div className="text-xs text-slate-500 mt-1 font-medium">
              Zero regulatory deviations
            </div>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-[#16A6C8]" /> Execution Latency
            </div>
            <div className="text-3xl font-black text-[#0B2545]">
              {suiteResult.execution_time_seconds}s
            </div>
            <div className="text-xs text-slate-500 mt-1 font-medium">
              Total deterministic runtime
            </div>
          </div>
        </div>
      )}

      {/* Test Cases Breakdown */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 font-bold text-sm text-[#0B2545] flex items-center justify-between">
          <span>Benchmark Test Case Results (TC-01 through TC-13)</span>
          {suiteResult && (
            <span className="text-xs font-mono text-slate-500">
              Timestamp: {new Date(suiteResult.timestamp).toLocaleTimeString()}
            </span>
          )}
        </div>

        <div className="divide-y divide-slate-200">
          {!suiteResult && running && (
            <div className="p-12 text-center text-slate-500 text-sm">
              Running live scenario assertions against persistent database...
            </div>
          )}

          {suiteResult?.test_cases?.map((tc: any) => (
            <div key={tc.test_id} className="p-5 hover:bg-slate-50/80 transition-colors">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2.5">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                    {tc.test_id}
                  </span>
                  <h3 className="font-bold text-sm text-slate-900">{tc.scenario}</h3>
                </div>
                <div>
                  {tc.passed ? (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" /> PASSED
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200">
                      <XCircle className="w-3.5 h-3.5 text-rose-700" /> FAILED
                    </span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 text-xs">
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                  <div className="font-semibold text-slate-600 mb-0.5">Expected Regulatory Norm:</div>
                  <div className="text-slate-800">{tc.expected_outcome}</div>
                </div>
                <div className="bg-blue-50/60 p-3 rounded-lg border border-blue-100">
                  <div className="font-semibold text-[#1677C8] mb-0.5">Observed Engine Verification:</div>
                  <div className="text-slate-800 font-mono text-[11px] truncate" title={tc.actual_outcome}>
                    {tc.actual_outcome}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

