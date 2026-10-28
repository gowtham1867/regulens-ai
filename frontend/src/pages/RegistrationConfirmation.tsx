import React from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import {
  Shield,
  CheckCircle2,
  Clock,
  Building2,
  Mail,
  User,
  ArrowRight,
  BadgeCheck,
  FileText,
  HelpCircle
} from "lucide-react";

export const RegistrationConfirmation: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const state = (location.state as any) || {};

  const institutionName = state.institution_name || "Registered Institution";
  const aicteId = state.aicte_id || "Generated during scrutiny";
  const email = state.email || "Registered Administrator Email";
  const fullName = state.full_name || "Authorized Representative";
  const submittedAt = state.submitted_at
    ? new Date(state.submitted_at).toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : new Date().toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
      });

  return (
    <div className="min-h-screen bg-[#F6F6F4] flex flex-col justify-between py-6 px-4 sm:px-6 lg:px-8 font-sans text-[#241C15]">
      {/* Top Header */}
      <header className="max-w-3xl mx-auto w-full flex items-center justify-between pb-4">
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

        <div className="hidden sm:flex items-center gap-2 text-xs font-semibold text-slate-600 bg-white px-3.5 py-1.5 rounded-full border border-[#E5E5E2] shadow-2xs">
          <BadgeCheck className="w-4 h-4 text-[#007C89]" />
          <span>Registration Receipt</span>
        </div>
      </header>

      {/* Main Confirmation Card */}
      <main className="w-full max-w-xl mx-auto my-auto py-4">
        <div className="bg-white rounded-2xl border border-[#E2E2DF] shadow-xs p-7 sm:p-10">
          {/* Status Icon */}
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-amber-50 border border-amber-200 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-xs">
              <Clock className="w-8 h-8 text-amber-600 animate-pulse" />
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-100/80 text-amber-800 text-[11px] font-bold uppercase tracking-wider mb-2">
              <span>Status: Pending AICTE Verification</span>
            </div>

            <h1 className="text-2xl font-bold text-[#241C15] tracking-tight">
              Registration Submitted Successfully
            </h1>
            <p className="mt-1 text-xs text-[#555555] font-normal leading-relaxed max-w-md mx-auto">
              Your institutional account request has been recorded and submitted to the AICTE Scrutiny Officers for nodal verification.
            </p>
          </div>

          {/* Registration Details Summary Box */}
          <div className="border border-[#E2E2DF] rounded-xl p-4.5 bg-[#FAFBFB] space-y-3 mb-6">
            <div className="flex items-center justify-between pb-2.5 border-b border-[#E5E5E2] text-xs">
              <span className="text-slate-500 font-medium">Institution Name:</span>
              <span className="font-bold text-[#0B2545] text-right max-w-[260px] truncate">
                {institutionName}
              </span>
            </div>

            <div className="flex items-center justify-between pb-2.5 border-b border-[#E5E5E2] text-xs">
              <span className="text-slate-500 font-medium">AICTE / Reference ID:</span>
              <span className="font-mono font-bold text-slate-800">
                {aicteId}
              </span>
            </div>

            <div className="flex items-center justify-between pb-2.5 border-b border-[#E5E5E2] text-xs">
              <span className="text-slate-500 font-medium">Administrator Name:</span>
              <span className="font-semibold text-slate-800">
                {fullName}
              </span>
            </div>

            <div className="flex items-center justify-between pb-2.5 border-b border-[#E5E5E2] text-xs">
              <span className="text-slate-500 font-medium">Work Email (Login ID):</span>
              <span className="font-mono font-semibold text-[#007C89]">
                {email}
              </span>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-500 font-medium">Submission Timestamp:</span>
              <span className="font-medium text-slate-600">
                {submittedAt}
              </span>
            </div>
          </div>

          {/* Regulatory Next Steps Callout */}
          <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/50 text-xs text-slate-700 space-y-2 mb-6">
            <div className="font-bold text-[#0B2545] flex items-center gap-1.5">
              <HelpCircle className="w-4 h-4 text-[#1677C8]" />
              <span>What happens next?</span>
            </div>
            <p className="leading-relaxed text-slate-600 text-[11px]">
              In accordance with AICTE Approval Process Handbook (APH) protocols, newly registered institutions undergo verification by AICTE Officers to prevent unauthorized duplicate profiles. Once nodal officers verify your institution, full regulatory filing features will be activated.
            </p>
          </div>

          {/* Action Button */}
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="w-full py-3 px-4 rounded-lg bg-[#007C89] hover:bg-[#006570] text-white font-bold text-sm tracking-wide shadow-xs transition-colors flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Proceed to Institution Login</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-3xl mx-auto w-full text-center text-xs text-slate-400 py-2">
        <p>
          © 2026 All India Council for Technical Education (AICTE) • ReguLens AI Regulatory Compliance Engine
        </p>
      </footer>
    </div>
  );
};

