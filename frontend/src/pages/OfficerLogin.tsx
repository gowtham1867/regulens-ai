import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Shield,
  Eye,
  EyeOff,
  AlertCircle,
  KeyRound,
  HelpCircle,
  BadgeCheck,
  ArrowLeft,
  ArrowRight,
  X,
  Lock
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export const OfficerLogin: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  // Officer Login Form State
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Helper modals / trays
  const [showDemoTray, setShowDemoTray] = useState(false);
  const [showForgotModal, setShowForgotModal] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError("Please enter your AICTE member registered email or username and password.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const user = await login(email.trim(), password, "OFFICER");
      if (user.role === "INSTITUTION_USER") {
        setError(
          "Access Denied: Institutional user accounts cannot access the AICTE Scrutiny Officer Portal. Please sign in via the Institution Login page."
        );
        return;
      }
      navigate("/");
    } catch (err: any) {
      const msg = err.message || "Invalid AICTE member credentials.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-[#F6F6F4] flex flex-col justify-between py-6 px-4 sm:px-6 lg:px-8 font-sans text-[#241C15]">
      {/* Top Header with ReguLens AI Branding and Return Link */}
      <header className="max-w-7xl mx-auto w-full flex items-center justify-between pb-4">
        <Link to="/login" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl bg-[#0B2545] flex items-center justify-center text-white shadow-xs group-hover:bg-[#123B63] transition-colors">
            <Shield className="w-5 h-5 text-[#16A6C8]" />
          </div>
          <div>
            <div className="font-extrabold text-lg tracking-tight text-[#0B2545] leading-none flex items-center">
              <span>ReguLens</span>
              <span className="text-[#007C89] ml-1">AI</span>
            </div>
            <div className="text-[11px] text-slate-500 font-medium tracking-wide mt-0.5">
              Evidence-Driven Regulatory Intelligence
            </div>
          </div>
        </Link>

        <div className="flex items-center gap-3">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-[#007C89] transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Institution Portal</span>
          </Link>
          <div className="hidden sm:flex items-center gap-2 text-xs font-semibold text-[#0B2545] bg-blue-50 px-3.5 py-1.5 rounded-full border border-blue-200 shadow-2xs">
            <BadgeCheck className="w-4 h-4 text-[#1677C8]" />
            <span>AICTE Member Gateway</span>
          </div>
        </div>
      </header>

      {/* Main Centered Login Card */}
      <main className="w-full max-w-[480px] mx-auto my-auto py-4">
        <div className="bg-white rounded-2xl border border-[#E2E2DF] shadow-xs p-7 sm:p-10">
          {/* Heading */}
          <div className="mb-6">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#0B2545]/5 text-[#0B2545] text-[11px] font-bold uppercase tracking-wider mb-2">
              <Lock className="w-3 h-3 text-[#0B2545]" />
              <span>Official Regulatory Access</span>
            </div>
            <h1 className="text-2xl font-bold text-[#241C15] tracking-tight">
              AICTE Member Login
            </h1>
            <p className="mt-1 text-xs text-[#555555] font-normal leading-relaxed">
              Access the official regulatory scrutiny and verification portal.
            </p>
          </div>

          {/* Inline Error Banner */}
          {error && (
            <div
              role="alert"
              className="mb-5 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5 animate-in fade-in duration-150"
            >
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <span className="leading-relaxed font-medium">{error}</span>
                {error.includes("Institutional user accounts") && (
                  <div className="mt-2">
                    <Link
                      to="/login"
                      className="inline-flex items-center gap-1 font-bold text-[#007C89] hover:underline"
                    >
                      <span>Return to Institution Login</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="officer-email"
                className="block text-xs font-semibold text-[#241C15] mb-1.5"
              >
                AICTE member's registered email or username
              </label>
              <input
                id="officer-email"
                type="text"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="e.g. officer@aicte-india.org"
                className="w-full px-3.5 py-2.5 rounded-lg border border-[#D0D0CD] bg-white text-sm text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#0B2545] focus:ring-1 focus:ring-[#0B2545] transition-all"
              />
            </div>

            <div>
              <label
                htmlFor="officer-password"
                className="block text-xs font-semibold text-[#241C15] mb-1.5"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="officer-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="Enter your member password"
                  className="w-full pl-3.5 pr-10 py-2.5 rounded-lg border border-[#D0D0CD] bg-white text-sm text-[#241C15] placeholder:text-slate-400 focus:outline-none focus:border-[#0B2545] focus:ring-1 focus:ring-[#0B2545] transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-[#241C15] p-1 cursor-pointer transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Forgot Password Link */}
            <div className="flex items-center justify-end pt-1">
              <button
                type="button"
                onClick={() => setShowForgotModal(true)}
                className="text-xs font-semibold text-[#007C89] hover:underline cursor-pointer"
              >
                Forgot password?
              </button>
            </div>

            {/* Prominent Navy Sign In Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 rounded-lg bg-[#0B2545] hover:bg-[#123B63] text-white font-bold text-sm tracking-wide shadow-xs transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Verifying AICTE Member...</span>
                </>
              ) : (
                <span>Sign in as AICTE Member</span>
              )}
            </button>
          </form>

          {/* BACK TO INSTITUTION LOGIN DIVIDER & LINK */}
          <div className="mt-8 pt-5 border-t border-[#E5E5E2] text-center">
            <div className="text-xs text-slate-500 mb-2">
              Looking for institutional application filing?
            </div>
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-[#007C89] hover:text-[#006570] hover:underline"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Institution Login</span>
            </Link>
          </div>

          {/* Test Credentials Directory Helper */}
          <div className="mt-6 pt-4 border-t border-[#E5E5E2] text-xs">
            <button
              type="button"
              onClick={() => setShowDemoTray(!showDemoTray)}
              className="w-full flex items-center justify-between text-slate-600 hover:text-[#0B2545] font-semibold transition-colors cursor-pointer py-1"
            >
              <span className="flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5 text-[#0B2545]" />
                <span>Test Credentials Directory</span>
              </span>
              <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full font-medium">
                {showDemoTray ? "Hide" : "Show 1-Click Fill"}
              </span>
            </button>

            {showDemoTray && (
              <div className="mt-3.5 space-y-2 animate-in fade-in duration-150">
                <div
                  onClick={() => fillDemo("officer@aicte-india.org", "Officer@123")}
                  className="p-2.5 bg-[#F6F6F4] rounded-lg border border-[#E0E0DC] hover:border-[#0B2545] transition-all cursor-pointer flex items-center justify-between group"
                >
                  <div>
                    <div className="font-bold text-[#241C15] text-xs flex items-center gap-1.5">
                      <Shield className="w-3.5 h-3.5 text-[#0B2545]" />
                      <span>AICTE Officer (Priya V. Sundaram)</span>
                    </div>
                    <div className="text-[11px] font-mono text-slate-500 mt-0.5">
                      officer@aicte-india.org / Officer@123
                    </div>
                  </div>
                  <span className="text-[10px] font-bold text-[#0B2545] opacity-0 group-hover:opacity-100 transition-opacity">
                    Fill
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto w-full text-center text-xs text-slate-400 py-2">
        <p>
          © 2026 All India Council for Technical Education (AICTE) • ReguLens AI Regulatory Compliance Engine
        </p>
      </footer>

      {/* Forgot Password Guidance Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-2xs p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-[#E2E2DF] animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-[#E5E5E2]">
              <div className="flex items-center gap-2">
                <HelpCircle className="w-5 h-5 text-[#0B2545]" />
                <h3 className="font-bold text-sm text-[#241C15]">
                  AICTE Officer Password Recovery
                </h3>
              </div>
              <button
                onClick={() => setShowForgotModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-md cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-4 text-xs space-y-3 text-slate-600 leading-relaxed">
              <p>
                AICTE Scrutiny Officer access keys are managed centrally through the AICTE Central Nodal Directory.
              </p>
              <div className="p-3 bg-[#F6F6F4] rounded-lg border border-[#E0E0DC]">
                <div className="font-bold text-[#241C15] mb-1">
                  AICTE Internal IT Systems Division:
                </div>
                <div className="text-[11px]">
                  Internal Portal: <span className="font-mono font-bold text-[#007C89]">portal.aicte-india.org/reset</span>
                </div>
                <div className="text-[11px] mt-0.5">
                  Internal Extension: <span className="font-mono font-bold">Ext 4492 (Nodal IT)</span>
                </div>
              </div>
              <p className="text-[11px] text-slate-500">
                For evaluator testing, use the provided test credentials in the directory below the login card.
              </p>
            </div>

            <div className="flex justify-end pt-2 border-t border-[#E5E5E2]">
              <button
                type="button"
                onClick={() => setShowForgotModal(false)}
                className="px-4 py-2 rounded-lg bg-[#0B2545] hover:bg-[#123B63] text-white font-bold text-xs cursor-pointer"
              >
                Understood
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
