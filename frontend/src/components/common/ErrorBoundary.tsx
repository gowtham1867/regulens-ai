import React, { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertOctagon, RefreshCw, LogOut, Home, ChevronDown, ChevronUp } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    showDetails: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
      showDetails: false,
    };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ReguLens AI UI Exception Caught by ErrorBoundary:", error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  private handleClearStorageAndLogin = () => {
    try {
      localStorage.removeItem("regulens_token");
      localStorage.removeItem("regulens_user");
      sessionStorage.clear();
    } catch {}
    window.location.href = "/login";
  };

  private handleGoHome = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = "/";
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#F4F7FB] flex items-center justify-center p-6 text-slate-800 font-sans">
          <div className="max-w-2xl w-full bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
            {/* Header */}
            <div className="bg-[#0B2545] p-6 text-white flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-rose-600/20 border border-rose-500/40 flex items-center justify-center shrink-0">
                <AlertOctagon className="w-7 h-7 text-rose-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs uppercase font-mono font-bold tracking-wider text-[#16A6C8]">
                    ReguLens AI • Runtime Protection
                  </span>
                </div>
                <h1 className="text-lg font-bold text-white mt-0.5">
                  Application Workspace Recovered
                </h1>
                <p className="text-xs text-slate-300 mt-1">
                  A client-side UI error was caught safely to protect data integrity and avoid application crash.
                </p>
              </div>
            </div>

            {/* Body */}
            <div className="p-6 space-y-4">
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900 leading-relaxed">
                <strong>Exception:</strong>{" "}
                <span className="font-mono">{this.state.error?.message || "Unknown client-side exception"}</span>
              </div>

              {/* Troubleshooting suggestions */}
              <div className="text-xs text-slate-600 space-y-2 bg-slate-50 p-4 rounded-xl border border-slate-200">
                <div className="font-bold text-slate-800">Recommended Recovery Actions:</div>
                <ul className="list-disc pl-5 space-y-1">
                  <li>Reload the page to re-initialize application components.</li>
                  <li>Clear stored session cache if state corruption occurred after recent updates.</li>
                  <li>Verify the backend server is reachable on <code className="bg-slate-200 px-1 py-0.5 rounded font-mono">http://127.0.0.1:8000</code>.</li>
                </ul>
              </div>

              {/* Collapsible Details */}
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button
                  type="button"
                  onClick={() => this.setState((prev) => ({ showDetails: !prev.showDetails }))}
                  className="w-full px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 flex items-center justify-between cursor-pointer transition-colors"
                >
                  <span>Diagnostic Stack Trace</span>
                  {this.state.showDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                {this.state.showDetails && (
                  <div className="p-4 bg-slate-900 text-slate-200 text-[11px] font-mono overflow-x-auto max-h-64 whitespace-pre">
                    {this.state.error?.stack || "No stack trace available."}
                    {"\n\nComponent Stack:"}
                    {this.state.errorInfo?.componentStack || "\nNo component stack available."}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-wrap items-center gap-3 justify-end">
                <button
                  type="button"
                  onClick={this.handleClearStorageAndLogin}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Clear Cache & Re-login</span>
                </button>
                <button
                  type="button"
                  onClick={this.handleGoHome}
                  className="px-4 py-2 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  <Home className="w-3.5 h-3.5" />
                  <span>Dashboard</span>
                </button>
                <button
                  type="button"
                  onClick={this.handleReset}
                  className="px-4 py-2 rounded-lg bg-[#0B2545] hover:bg-[#123B63] text-white text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Reload Application</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
