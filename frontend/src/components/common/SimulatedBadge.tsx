import React from "react";
import { Info } from "lucide-react";

interface SimulatedBadgeProps {
  label?: string;
  className?: string;
}

export const SimulatedBadge: React.FC<SimulatedBadgeProps> = ({
  label = "SIMULATED VERIFICATION — DEMONSTRATION DATA",
  className = "",
}) => {
  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-50 text-amber-900 border border-amber-300 shadow-xs ${className}`}
      title="This outcome was produced by a deterministic simulated test adapter without connecting to live state ministry registries."
    >
      <Info className="w-3.5 h-3.5 text-amber-700 shrink-0" />
      <span>{label}</span>
    </div>
  );
};

