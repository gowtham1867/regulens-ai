import React from "react";
import { Shield, Sparkles, Building2, CheckCircle2 } from "lucide-react";

export const AuthBranding: React.FC<{ subtitle?: string; roleBadge?: string }> = ({
  subtitle = "Evidence-Driven Regulatory Intelligence",
  roleBadge,
}) => {
  return (
    <div className="text-center sm:mx-auto sm:w-full sm:max-w-md">
      {/* Official Emblem Logo */}
      <div className="mx-auto flex items-center justify-center">
        <div className="relative">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#0B2545] to-[#123B63] border-2 border-[#1677C8] flex items-center justify-center shadow-lg shadow-blue-950/20 text-white">
            <Shield className="w-7 h-7 text-[#16A6C8]" />
          </div>
          <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-[#1677C8] rounded-full border-2 border-white flex items-center justify-center">
            <Sparkles className="w-2.5 h-2.5 text-white" />
          </div>
        </div>
      </div>

      {/* Main Title & Tagline */}
      <div className="mt-3.5">
        <h1 className="text-2xl font-black tracking-tight text-[#0B2545] flex items-center justify-center gap-1.5">
          <span>ReguLens</span>
          <span className="text-[#1677C8]">AI</span>
        </h1>
        <p className="mt-1 text-xs font-bold text-slate-600 tracking-wider uppercase">
          {subtitle}
        </p>
        <p className="text-[11px] text-slate-500 mt-0.5">
          All India Council for Technical Education (AICTE)
        </p>
      </div>

      {/* Role Badge if provided */}
      {roleBadge && (
        <div className="mt-2.5 inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-blue-50 border border-blue-200 text-[11px] font-semibold text-[#0B2545]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#1677C8] animate-pulse"></span>
          <span>{roleBadge}</span>
        </div>
      )}
    </div>
  );
};

