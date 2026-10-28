import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  FileText,
  Network,
  ShieldCheck,
  BookOpen,
  HelpCircle,
  History,
  Activity,
  Layers,
  Building2,
  UserCheck
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const isOfficerOrAdmin = user?.role === "AICTE_OFFICER" || user?.role === "ADMINISTRATOR";

  const navLinks = [
    { to: "/", label: "Overview Dashboard", icon: LayoutDashboard },
    { to: "/applications", label: "Applications Queue", icon: FileText },
    { to: "/trustgraph", label: "TrustGraph Registry", icon: Network },
    { to: "/verification", label: "Issuer Verification", icon: ShieldCheck },
    { to: "/rules", label: "Compliance Rules", icon: BookOpen },
    { to: "/clarifications", label: "Clarification Requests", icon: HelpCircle },
    { to: "/audit", label: "Audit Trail", icon: History, officerOnly: true },
    { to: "/evaluation", label: "Benchmark Suite", icon: Activity, officerOnly: true },
  ];

  return (
    <aside className="w-64 bg-[#0B2545] text-slate-100 flex flex-col shrink-0 min-h-screen border-r border-[#123B63]">
      {/* Brand Header */}
      <div className="p-5 border-b border-[#123B63]/80 bg-[#091D36]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[#1677C8] to-[#16A6C8] flex items-center justify-center font-bold text-white shadow-md text-lg tracking-wider">
            RL
          </div>
          <div>
            <div className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
              <span>ReguLens</span>
              <span className="text-[#16A6C8] font-black">AI</span>
            </div>
            <div className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">
              Regulatory Intelligence
            </div>
          </div>
        </div>
        <div className="mt-3 text-[11px] text-slate-400 leading-snug border-t border-[#123B63]/60 pt-2">
          Evidence-Driven Scrutiny for AICTE
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
          {user?.role === "INSTITUTION_USER" ? "Institution Portal" : "Scrutiny Portal"}
        </div>

        {navLinks.map((item) => {
          if (item.officerOnly && !isOfficerOrAdmin) return null;
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-[#1677C8] text-white shadow-sm font-semibold"
                    : "text-slate-300 hover:bg-[#123B63] hover:text-white"
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0 text-slate-400 group-hover:text-white" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* User / Institute Footer */}
      <div className="p-4 border-t border-[#123B63] bg-[#091D36]/80 text-xs text-slate-300">
        <div className="flex items-center gap-2 mb-1.5">
          {user?.role === "INSTITUTION_USER" ? (
            <Building2 className="w-4 h-4 text-[#16A6C8] shrink-0" />
          ) : (
            <UserCheck className="w-4 h-4 text-[#16A6C8] shrink-0" />
          )}
          <span className="font-semibold text-white truncate">
            {user?.role === "INSTITUTION_USER"
              ? user.institution_name || "Institution"
              : user?.full_name}
          </span>
        </div>
        <div className="text-[11px] text-slate-400 font-mono tracking-wide">
          Role: <span className="text-slate-200">{user?.role?.replace(/_/g, " ")}</span>
        </div>
      </div>
    </aside>
  );
};

