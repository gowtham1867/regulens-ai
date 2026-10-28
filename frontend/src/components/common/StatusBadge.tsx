import React from "react";
import { CheckCircle2, AlertTriangle, XCircle, Clock, Eye, AlertCircle, RefreshCw } from "lucide-react";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = "md" }) => {
  const norm = (status || "").toUpperCase();
  const isSm = size === "sm";

  if (norm === "PASSED" || norm === "VERIFIED" || norm === "APPROVED") {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 ${isSm ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"}`}>
        <CheckCircle2 className={isSm ? "w-3 h-3 text-emerald-600" : "w-3.5 h-3.5 text-emerald-600"} />
        <span>{norm}</span>
      </span>
    );
  }

  if (norm === "FAILED" || norm === "REJECTED" || norm === "EXPIRED" || norm === "CRITICAL") {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-rose-50 text-rose-800 border border-rose-200 ${isSm ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"}`}>
        <XCircle className={isSm ? "w-3 h-3 text-rose-600" : "w-3.5 h-3.5 text-rose-600"} />
        <span>{norm}</span>
      </span>
    );
  }

  if (norm === "WARNING" || norm === "MAJOR" || norm === "RETURNED" || norm === "CLARIFICATION_REQUESTED") {
    const label = norm === "CLARIFICATION_REQUESTED" ? "CLARIFICATION REQUIRED" : norm;
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-amber-50 text-amber-800 border border-amber-200 ${isSm ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"}`}>
        <AlertTriangle className={isSm ? "w-3 h-3 text-amber-600" : "w-3.5 h-3.5 text-amber-600"} />
        <span>{label}</span>
      </span>
    );
  }

  if (norm === "MANUAL_REVIEW_REQUIRED" || norm === "UNDER_REVIEW") {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-sky-50 text-sky-800 border border-sky-200 ${isSm ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"}`}>
        <Eye className={isSm ? "w-3 h-3 text-sky-600" : "w-3.5 h-3.5 text-sky-600"} />
        <span>{norm.replace(/_/g, " ")}</span>
      </span>
    );
  }

  if (norm === "CORRECTION_SUBMITTED" || norm === "REVALIDATION") {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200 ${isSm ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"}`}>
        <RefreshCw className={isSm ? "w-3 h-3 text-indigo-600 animate-spin" : "w-3.5 h-3.5 text-indigo-600"} />
        <span>{norm.replace(/_/g, " ")}</span>
      </span>
    );
  }

  if (norm === "SOURCE_UNAVAILABLE") {
    return (
      <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-gray-100 text-gray-800 border border-gray-300 ${isSm ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"}`}>
        <AlertCircle className={isSm ? "w-3 h-3 text-gray-500" : "w-3.5 h-3.5 text-gray-500"} />
        <span>SOURCE UNAVAILABLE</span>
      </span>
    );
  }

  // Fallback
  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-slate-100 text-slate-700 border border-slate-200 ${isSm ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"}`}>
      <Clock className={isSm ? "w-3 h-3 text-slate-500" : "w-3.5 h-3.5 text-slate-500"} />
      <span>{norm.replace(/_/g, " ")}</span>
    </span>
  );
};

