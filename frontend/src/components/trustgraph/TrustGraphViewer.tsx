import React, { useState, useMemo, useRef } from "react";
import {
  Network,
  Table,
  FileText,
  AlertTriangle,
  Copy,
  History,
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Eye,
  Layers,
  ArrowRight,
  ExternalLink,
  ChevronRight,
  Filter,
} from "lucide-react";
import type {
  TrustGraphData,
  TrustGraphNode,
  TrustGraphEdge,
  ContradictoryClaim,
  DuplicateCandidate,
  RelationshipTriplet,
  ExtractedClaimItem,
} from "../../types";

interface TrustGraphViewerProps {
  data: TrustGraphData | null;
  loading?: boolean;
}

const TIER_COLUMNS = [
  { tier: 0, title: "TIER 0: INSTITUTION / BASELINE", x: 40, width: 230, color: "#3B82F6" },
  { tier: 1, title: "TIER 1: APPLICATION & CLAIMS", x: 310, width: 230, color: "#0EA5E9" },
  { tier: 2, title: "TIER 2: DOCUMENTS & EVIDENCE", x: 580, width: 230, color: "#14B8A6" },
  { tier: 3, title: "TIER 3: CLAIMS & VERIFICATIONS", x: 850, width: 240, color: "#F59E0B" },
  { tier: 4, title: "TIER 4: FINDINGS & DECISIONS", x: 1130, width: 240, color: "#EF4444" },
];

export const TrustGraphViewer: React.FC<TrustGraphViewerProps> = ({ data, loading }) => {
  const [activeTab, setActiveTab] = useState<
    "canvas" | "triplets" | "claims" | "contradictions" | "duplicates" | "history"
  >("canvas");

  const [selectedFindingId, setSelectedFindingId] = useState<string>("ALL");
  const [filterType, setFilterType] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedNode, setSelectedNode] = useState<TrustGraphNode | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const canvasRef = useRef<HTMLDivElement>(null);

  // Compute Active Finding Path Nodes
  const activePathNodes = useMemo<Set<string>>(() => {
    if (!data?.finding_paths || selectedFindingId === "ALL") return new Set<string>();
    const nodeIds = data.finding_paths[selectedFindingId] || [];
    return new Set<string>(nodeIds);
  }, [data, selectedFindingId]);

  // Compute Node Positions on 5-Tier Canvas
  const { nodePositions, canvasHeight } = useMemo(() => {
    if (!data?.nodes) return { nodePositions: {}, canvasHeight: 650 };

    const positions: Record<string, { x: number; y: number; width: number; height: number }> = {};
    const tierNodeBuckets: Record<number, TrustGraphNode[]> = { 0: [], 1: [], 2: [], 3: [], 4: [] };

    data.nodes.forEach((n) => {
      const t = typeof n.tier === "number" ? n.tier : 0;
      if (tierNodeBuckets[t]) {
        tierNodeBuckets[t].push(n);
      } else {
        tierNodeBuckets[0].push(n);
      }
    });

    let maxNodesInTier = 0;
    Object.values(tierNodeBuckets).forEach((b) => {
      if (b.length > maxNodesInTier) maxNodesInTier = b.length;
    });

    const startY = 110;
    const nodeHeight = 85;
    const nodeGap = 24;

    TIER_COLUMNS.forEach((col) => {
      const bucket = tierNodeBuckets[col.tier] || [];
      bucket.forEach((node, idx) => {
        positions[node.id] = {
          x: col.x,
          y: startY + idx * (nodeHeight + nodeGap),
          width: col.width,
          height: nodeHeight,
        };
      });
    });

    const totalHeight = Math.max(680, startY + maxNodesInTier * (nodeHeight + nodeGap) + 80);
    return { nodePositions: positions, canvasHeight: totalHeight };
  }, [data]);

  // Extract all findings for the Finding Path selector
  const findingsList = useMemo(() => {
    if (!data?.nodes) return [];
    return data.nodes.filter((n) => n.type === "FINDING");
  }, [data]);

  if (loading) {
    return (
      <div className="bg-[#0A192F] rounded-2xl p-12 text-center text-slate-400 border border-[#1E3A5F]">
        <div className="animate-spin w-8 h-8 border-2 border-[#16A6C8] border-t-transparent rounded-full mx-auto mb-3" />
        <p className="text-sm font-semibold">Generating TrustGraph Evidence Topology...</p>
      </div>
    );
  }

  if (!data || data.nodes.length === 0) {
    return (
      <div className="bg-[#0A192F] rounded-2xl p-12 text-center border border-[#1E3A5F] text-slate-300">
        <Network className="w-12 h-12 text-slate-500 mx-auto mb-3" />
        <h3 className="text-base font-bold text-white mb-1">
          No evidence relationships are available for this application.
        </h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Upload regulatory certificates and execute compliance validation to construct the 5-tier cryptographic TrustGraph provenance registry.
        </p>
      </div>
    );
  }

  const getNodeColor = (node: TrustGraphNode, isPathNode: boolean, isDimmed: boolean) => {
    const isFailed = node.status === "DEFICIENT" || node.status === "FAILED" || node.status === "REJECTED";
    const isWarning = node.status === "WARNING" || node.status === "DISCREPANCY";
    const isSuccess =
      node.status === "PASSED" ||
      node.status === "VERIFIED" ||
      node.status === "APPROVED" ||
      node.status === "SUCCESS";

    let border = "border-slate-700";
    let bg = "bg-[#0E2038]";
    let text = "text-slate-200";
    let badgeBg = "bg-slate-800 text-slate-300";

    if (isFailed) {
      border = "border-rose-500/80 shadow-[0_0_12px_rgba(244,63,94,0.3)]";
      bg = "bg-rose-950/40";
      text = "text-rose-200";
      badgeBg = "bg-rose-900/80 text-rose-300";
    } else if (isWarning) {
      border = "border-amber-500/80 shadow-[0_0_12px_rgba(245,158,11,0.25)]";
      bg = "bg-amber-950/40";
      text = "text-amber-200";
      badgeBg = "bg-amber-900/80 text-amber-300";
    } else if (isSuccess) {
      border = "border-emerald-500/80 shadow-[0_0_12px_rgba(16,185,129,0.25)]";
      bg = "bg-emerald-950/40";
      text = "text-emerald-200";
      badgeBg = "bg-emerald-900/80 text-emerald-300";
    }

    if (isPathNode) {
      border = "border-cyan-400 ring-2 ring-cyan-400/50 shadow-[0_0_16px_rgba(34,211,238,0.5)]";
      bg = "bg-[#0B2A4A]";
    }

    return { border, bg, text, badgeBg, opacity: isDimmed ? 0.15 : 1.0 };
  };

  return (
    <div className="space-y-4">
      {/* TrustGraph Sub-Navigation Tabs */}
      <div className="bg-[#0B1E36] p-2 rounded-2xl border border-[#1A365D] flex flex-wrap items-center justify-between gap-3 shadow-md">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setActiveTab("canvas")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === "canvas"
                ? "bg-[#1677C8] text-white shadow-md shadow-blue-900/50"
                : "text-slate-300 hover:text-white hover:bg-slate-800/60"
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            <span>Interactive 5-Tier Canvas</span>
          </button>

          <button
            onClick={() => setActiveTab("triplets")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === "triplets"
                ? "bg-[#1677C8] text-white shadow-md shadow-blue-900/50"
                : "text-slate-300 hover:text-white hover:bg-slate-800/60"
            }`}
          >
            <Table className="w-3.5 h-3.5" />
            <span>Relationship Table ({data.edges?.length || 0})</span>
          </button>

          <button
            onClick={() => setActiveTab("claims")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === "claims"
                ? "bg-[#1677C8] text-white shadow-md shadow-blue-900/50"
                : "text-slate-300 hover:text-white hover:bg-slate-800/60"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Extracted Claims ({data.extracted_claims?.length || 0})</span>
          </button>

          <button
            onClick={() => setActiveTab("contradictions")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === "contradictions"
                ? "bg-[#1677C8] text-white shadow-md shadow-blue-900/50"
                : "text-slate-300 hover:text-white hover:bg-slate-800/60"
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            <span>Contradictory Claims ({data.contradictory_claims?.length || 0})</span>
          </button>

          <button
            onClick={() => setActiveTab("duplicates")}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
              activeTab === "duplicates"
                ? "bg-[#1677C8] text-white shadow-md shadow-blue-900/50"
                : "text-slate-300 hover:text-white hover:bg-slate-800/60"
            }`}
          >
            <Copy className="w-3.5 h-3.5 text-amber-400" />
            <span>Duplicate Candidates ({data.duplicate_candidates?.length || 0})</span>
          </button>
        </div>

        {/* Top Summary Badges */}
        <div className="flex items-center gap-2 text-[11px] font-mono pr-2">
          <span className="text-slate-400">Nodes:</span>
          <span className="text-cyan-400 font-bold">{data.summary?.total_nodes ?? data.nodes?.length ?? 0}</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">Edges:</span>
          <span className="text-emerald-400 font-bold">{data.summary?.total_edges ?? data.edges?.length ?? 0}</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">Findings:</span>
          <span className="text-rose-400 font-bold">{data.summary?.findings_count ?? 0}</span>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* VIEW 1: INTERACTIVE 5-TIER DARK CANVAS                                   */}
      {/* ========================================================================= */}
      {activeTab === "canvas" && (
        <div className="space-y-3">
          {/* Controls Bar */}
          <div className="bg-[#071325] p-3 rounded-xl border border-[#1E3A5F] flex flex-wrap items-center justify-between gap-3 text-xs">
            {/* Finding-Path Provenance Selector */}
            <div className="flex items-center gap-2 flex-1 min-w-[280px]">
              <label className="font-bold text-cyan-400 shrink-0 flex items-center gap-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
                <span>Trace Finding Provenance:</span>
              </label>
              <select
                value={selectedFindingId}
                onChange={(e) => setSelectedFindingId(e.target.value)}
                className="bg-[#0D223D] border border-cyan-500/40 text-cyan-200 rounded-lg px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-cyan-400 flex-1"
              >
                <option value="ALL">All Evidence Paths (No Focus)</option>
                {findingsList.map((f) => {
                  const fid = f.id.replace("finding_", "");
                  return (
                    <option key={f.id} value={fid}>
                      {f.label} ({f.metadata?.severity || f.status})
                    </option>
                  );
                })}
              </select>
              {selectedFindingId !== "ALL" && (
                <button
                  onClick={() => setSelectedFindingId("ALL")}
                  className="px-2 py-1 text-[11px] rounded bg-cyan-950 text-cyan-300 border border-cyan-800 hover:bg-cyan-900"
                >
                  Clear Trace
                </button>
              )}
            </div>

            {/* Keyword Search */}
            <div className="relative w-48">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search nodes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#0D223D] border border-[#1E3A5F] text-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:border-cyan-400"
              />
            </div>

            {/* Zoom Controls */}
            <div className="flex items-center gap-1 bg-[#0D223D] border border-[#1E3A5F] rounded-lg p-1">
              <button
                onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.1))}
                className="p-1 text-slate-300 hover:text-white hover:bg-slate-800 rounded"
                title="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <span className="text-[10px] font-mono px-1.5 text-slate-300">
                {Math.round(zoomLevel * 100)}%
              </span>
              <button
                onClick={() => setZoomLevel((z) => Math.min(1.4, z + 0.1))}
                className="p-1 text-slate-300 hover:text-white hover:bg-slate-800 rounded"
                title="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setZoomLevel(1.0)}
                className="p-1 text-slate-300 hover:text-white hover:bg-slate-800 rounded"
                title="Reset Zoom"
              >
                <RotateCcw className="w-3 h-3" />
              </button>
            </div>
          </div>

          {/* Graph Canvas Container */}
          <div
            ref={canvasRef}
            className="relative rounded-2xl border border-[#1A365D] bg-[#071325] overflow-auto shadow-2xl"
            style={{
              backgroundImage: "radial-gradient(circle, rgba(56, 189, 248, 0.12) 1px, transparent 1px)",
              backgroundSize: "24px 24px",
              minHeight: "620px",
              maxHeight: "780px",
            }}
          >
            {/* Inner Scaled Canvas */}
            <div
              style={{
                width: "1420px",
                height: `${canvasHeight}px`,
                transform: `scale(${zoomLevel})`,
                transformOrigin: "top left",
                position: "relative",
              }}
            >
              {/* Tier Column Headers */}
              {TIER_COLUMNS.map((col) => (
                <div
                  key={col.tier}
                  style={{
                    position: "absolute",
                    left: `${col.x}px`,
                    top: "20px",
                    width: `${col.width}px`,
                  }}
                  className="pb-2 border-b border-[#1E3A5F] flex items-center justify-between"
                >
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: col.color }}
                    />
                    <span className="text-[10px] font-bold tracking-wider text-slate-300 uppercase">
                      {col.title}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                    {data.nodes.filter((n) => n.tier === col.tier).length}
                  </span>
                </div>
              ))}

              {/* SVG Connectors Layer */}
              <svg
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  width: "1420px",
                  height: `${canvasHeight}px`,
                  pointerEvents: "none",
                }}
              >
                <defs>
                  <marker
                    id="arrowhead-default"
                    viewBox="0 0 10 10"
                    refX="9"
                    refY="5"
                    markerWidth="6"
                    markerHeight="6"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 1 L 10 5 L 0 9 z" fill="#3B82F6" opacity="0.7" />
                  </marker>
                  <marker
                    id="arrowhead-active"
                    viewBox="0 0 10 10"
                    refX="9"
                    refY="5"
                    markerWidth="7"
                    markerHeight="7"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#22D3EE" />
                  </marker>
                  <marker
                    id="arrowhead-contradiction"
                    viewBox="0 0 10 10"
                    refX="9"
                    refY="5"
                    markerWidth="7"
                    markerHeight="7"
                    orient="auto-start-reverse"
                  >
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#F43F5E" />
                  </marker>
                </defs>

                {data.edges.map((edge, idx) => {
                  const sPos = nodePositions[edge.source];
                  const tPos = nodePositions[edge.target];
                  if (!sPos || !tPos) return null;

                  const isEdgeActive =
                    activePathNodes.has(edge.source) && activePathNodes.has(edge.target);
                  const isDimmed =
                    selectedFindingId !== "ALL" && !isEdgeActive;

                  const isContradiction =
                    edge.type === "CONTRADICTION" || edge.label === "CONTRADICTS";

                  const sx = sPos.x < tPos.x ? sPos.x + sPos.width : sPos.x;
                  const sy = sPos.y + sPos.height / 2;
                  const tx = sPos.x < tPos.x ? tPos.x : tPos.x + tPos.width;
                  const ty = tPos.y + tPos.height / 2;

                  const dx = Math.abs(tx - sx) * 0.5;
                  const path = `M ${sx} ${sy} C ${sx + (tx > sx ? dx : -dx)} ${sy}, ${
                    tx - (tx > sx ? dx : -dx)
                  } ${ty}, ${tx} ${ty}`;

                  let strokeColor = "#2563EB";
                  let marker = "url(#arrowhead-default)";
                  let strokeWidth = 1.6;

                  if (isContradiction) {
                    strokeColor = "#F43F5E";
                    marker = "url(#arrowhead-contradiction)";
                    strokeWidth = 2.2;
                  } else if (isEdgeActive) {
                    strokeColor = "#22D3EE";
                    marker = "url(#arrowhead-active)";
                    strokeWidth = 2.6;
                  }

                  return (
                    <g key={idx} opacity={isDimmed ? 0.12 : 0.75}>
                      <path
                        d={path}
                        fill="none"
                        stroke={strokeColor}
                        strokeWidth={strokeWidth}
                        markerEnd={marker}
                        strokeDasharray={edge.type === "BASELINE" ? "4 4" : "none"}
                      />
                    </g>
                  );
                })}
              </svg>

              {/* Node Cards Layer */}
              {data.nodes.map((node) => {
                const pos = nodePositions[node.id];
                if (!pos) return null;

                const isPathNode = activePathNodes.has(node.id);
                const isDimmed = selectedFindingId !== "ALL" && !isPathNode;
                const isSelected = selectedNode?.id === node.id;
                const isHovered = hoveredNodeId === node.id;

                const styling = getNodeColor(node, isPathNode, isDimmed);

                const matchesSearch =
                  searchQuery.trim() === "" ||
                  node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
                  node.type.toLowerCase().includes(searchQuery.toLowerCase());

                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    onMouseEnter={() => setHoveredNodeId(node.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                    style={{
                      position: "absolute",
                      left: `${pos.x}px`,
                      top: `${pos.y}px`,
                      width: `${pos.width}px`,
                      height: `${pos.height}px`,
                      opacity: matchesSearch ? styling.opacity : 0.15,
                    }}
                    className={`rounded-xl p-3 border-2 cursor-pointer transition-all duration-200 ${
                      styling.border
                    } ${styling.bg} ${
                      isSelected ? "ring-2 ring-cyan-400 scale-[1.02] z-20" : "hover:scale-[1.01] z-10"
                    } ${isHovered ? "shadow-lg shadow-cyan-900/40" : ""}`}
                  >
                    <div className="flex items-center justify-between text-[9px] font-bold uppercase tracking-wider mb-1">
                      <span className="text-slate-400 font-mono">T{node.tier} • {node.type.replace(/_/g, " ")}</span>
                      <span className={`px-1.5 py-0.2 rounded font-mono ${styling.badgeBg}`}>
                        {node.status}
                      </span>
                    </div>

                    <div className={`font-bold text-xs truncate ${styling.text}`}>
                      {node.label}
                    </div>

                    <div className="text-[10px] text-slate-400 mt-1 flex items-center justify-between font-mono">
                      <span className="truncate max-w-[140px]">
                        {node.metadata?.file_hash
                          ? `SHA: ${node.metadata.file_hash.substring(0, 10)}...`
                          : node.metadata?.rule_code || node.id}
                      </span>
                      <span className="text-cyan-400 text-[10px] font-sans font-bold flex items-center gap-0.5">
                        Inspect <ChevronRight className="w-2.5 h-2.5" />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 2: RELATIONSHIP TABLE                                                */}
      {/* ========================================================================= */}
      {activeTab === "triplets" && (
        <div className="bg-[#071325] rounded-2xl p-5 border border-[#1E3A5F] shadow-xl text-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#1E3A5F]">
            <div>
              <h3 className="font-bold text-white text-sm">TrustGraph Relationship Triples</h3>
              <p className="text-xs text-slate-400">
                Formal cryptographic triplets connecting institutional declarations, evidence artifacts, and regulatory findings
              </p>
            </div>
            <div className="text-xs text-cyan-400 font-mono">
              Total Triples: {data.relationship_table?.length || data.edges.length}
            </div>
          </div>

          <div className="overflow-x-auto max-h-[500px]">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[#1E3A5F] text-[11px] font-bold uppercase text-slate-400">
                  <th className="py-2.5 px-3">Source Node (Subject)</th>
                  <th className="py-2.5 px-3">Tier</th>
                  <th className="py-2.5 px-3 text-cyan-400">Relationship (Predicate)</th>
                  <th className="py-2.5 px-3">Target Node (Object)</th>
                  <th className="py-2.5 px-3">Tier</th>
                  <th className="py-2.5 px-3">Assurance Level</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#162C4E] text-slate-300">
                {(data.relationship_table || []).map((t, i) => (
                  <tr key={i} className="hover:bg-[#0D223D] transition-colors">
                    <td className="py-2 px-3 font-semibold text-white">
                      {t.source_label}
                    </td>
                    <td className="py-2 px-3 font-mono text-[10px] text-slate-400">
                      Tier {t.source_tier}
                    </td>
                    <td className="py-2 px-3 font-mono text-cyan-300 font-bold">
                      --[{t.relation}]--&gt;
                    </td>
                    <td className="py-2 px-3 font-semibold text-slate-200">
                      {t.target_label}
                    </td>
                    <td className="py-2 px-3 font-mono text-[10px] text-slate-400">
                      Tier {t.target_tier}
                    </td>
                    <td className="py-2 px-3 font-mono text-[11px]">
                      <span className="px-2 py-0.5 rounded bg-blue-900/60 text-blue-300 font-bold">
                        {Math.round((t.confidence || 1.0) * 100)}% Conf.
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 3: EXTRACTED CLAIMS & ASSURANCE                                     */}
      {/* ========================================================================= */}
      {activeTab === "claims" && (
        <div className="bg-[#071325] rounded-2xl p-5 border border-[#1E3A5F] shadow-xl text-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#1E3A5F]">
            <div>
              <h3 className="font-bold text-white text-sm">Extracted Structured Claims & Assurance</h3>
              <p className="text-xs text-slate-400">
                Field-level claims harvested by PyMuPDF OCR from authentic PDF documents with layout page references
              </p>
            </div>
            <div className="text-xs text-emerald-400 font-mono">
              Claims Count: {data.extracted_claims?.length || 0}
            </div>
          </div>

          <div className="overflow-x-auto max-h-[500px]">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[#1E3A5F] text-[11px] font-bold uppercase text-slate-400">
                  <th className="py-2.5 px-3">Field Key / Label</th>
                  <th className="py-2.5 px-3">Document Title</th>
                  <th className="py-2.5 px-3">Extracted Value</th>
                  <th className="py-2.5 px-3">Normalized Value</th>
                  <th className="py-2.5 px-3">Source Page</th>
                  <th className="py-2.5 px-3">OCR Confidence</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#162C4E] text-slate-300">
                {(data.extracted_claims || []).map((c, i) => (
                  <tr key={i} className="hover:bg-[#0D223D] transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="font-bold text-white">{c.field_label}</div>
                      <div className="text-[10px] font-mono text-slate-400">{c.field_key}</div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-300">
                      <div>{c.document_title}</div>
                      <span className="text-[9px] font-mono px-1 rounded bg-slate-800 text-slate-400">
                        {c.version}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-cyan-200">
                      {c.extracted_value}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-300">
                      {c.normalized_value}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-slate-400">
                      Page {c.source_page}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      <span
                        className={`px-2 py-0.5 rounded font-bold ${
                          c.confidence >= 85
                            ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                            : "bg-amber-950 text-amber-300 border border-amber-800"
                        }`}
                      >
                        {c.confidence}%
                      </span>
                    </td>
                    <td className="py-2.5 px-3">
                      {c.is_manually_corrected ? (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-purple-950 text-purple-300 border border-purple-800 font-bold">
                          CORRECTED
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] bg-blue-950 text-blue-300 border border-blue-800 font-bold">
                          AI EXTRACTED
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 4: CONTRADICTORY CLAIMS & DISCREPANCIES                             */}
      {/* ========================================================================= */}
      {activeTab === "contradictions" && (
        <div className="bg-[#071325] rounded-2xl p-5 border border-[#1E3A5F] shadow-xl text-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#1E3A5F]">
            <div>
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <span>Cross-Evidence Contradictions & Shortfall Analysis</span>
              </h3>
              <p className="text-xs text-slate-400">
                Automated multi-modal discrepancy detection comparing declared values against extracted document evidence and baseline master data
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-rose-950 text-rose-300 border border-rose-800">
              {data.contradictory_claims?.length || 0} Contradictions Detected
            </span>
          </div>

          {!data.contradictory_claims || data.contradictory_claims.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
              <p className="font-bold text-white">No cross-document contradictions detected.</p>
              <p className="text-xs text-slate-500 mt-0.5">
                All declared institutional parameters match extracted evidence within regulatory tolerances.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.contradictory_claims.map((c) => (
                <div
                  key={c.id}
                  className="rounded-xl border border-rose-900/60 bg-[#0E1E34] p-4 space-y-3 shadow-md"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                      {c.severity} • {c.category}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">{c.id}</span>
                  </div>

                  <h4 className="font-bold text-sm text-white">{c.title}</h4>

                  {/* Side-by-Side Comparison Box */}
                  <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-[#071325] border border-slate-800">
                    <div className="space-y-1">
                      <div className="text-[10px] font-bold text-slate-400 uppercase">
                        {c.claim_label}
                      </div>
                      <div className="text-sm font-black text-rose-300 font-mono">
                        {c.claim_value}
                      </div>
                    </div>
                    <div className="space-y-1 border-l border-slate-800 pl-3">
                      <div className="text-[10px] font-bold text-slate-400 uppercase">
                        {c.evidence_label}
                      </div>
                      <div className="text-sm font-black text-emerald-300 font-mono">
                        {c.evidence_value}
                      </div>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-900/50 text-rose-200 text-xs">
                    <span className="font-bold">Discrepancy: </span>
                    <span>{c.discrepancy_delta}</span>
                    <p className="mt-1 text-slate-300 text-[11px] leading-relaxed">{c.explanation}</p>
                  </div>

                  <div className="text-[11px] text-amber-300 bg-amber-950/30 p-2 rounded border border-amber-900/40">
                    <span className="font-bold">Action Required: </span>
                    <span>{c.suggested_action}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* VIEW 5: DUPLICATE CANDIDATES                                             */}
      {/* ========================================================================= */}
      {activeTab === "duplicates" && (
        <div className="bg-[#071325] rounded-2xl p-5 border border-[#1E3A5F] shadow-xl text-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#1E3A5F]">
            <div>
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Copy className="w-4 h-4 text-amber-400" />
                <span>Cryptographic SHA-256 Collision & Duplicate Analysis</span>
              </h3>
              <p className="text-xs text-slate-400">
                Scans uploaded artifacts against all system submissions to prevent recycling land deeds, building plans, or NOCs across institutions
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-amber-950 text-amber-300 border border-amber-800">
              {data.duplicate_candidates?.length || 0} Duplicates Found
            </span>
          </div>

          {!data.duplicate_candidates || data.duplicate_candidates.length === 0 ? (
            <div className="p-8 text-center text-slate-400">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
              <p className="font-bold text-white">No duplicate document candidates detected.</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Every uploaded document has a unique SHA-256 cryptographic fingerprint.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {data.duplicate_candidates.map((dup) => (
                <div
                  key={dup.id}
                  className="p-4 rounded-xl border border-amber-900/60 bg-[#0E1E34] text-xs space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-sm">{dup.document_title}</span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                          dup.is_cross_institution
                            ? "bg-rose-950 text-rose-300 border border-rose-800"
                            : "bg-amber-950 text-amber-300 border border-amber-800"
                        }`}
                      >
                        {dup.is_cross_institution ? "CROSS-INSTITUTION REUSE" : "SAME INSTITUTION VERSION"}
                      </span>
                    </div>
                    <span className="font-mono text-slate-400 text-[10px]">
                      Match Score: {Math.round(dup.similarity_score * 100)}%
                    </span>
                  </div>

                  <p className="text-slate-300">{dup.description}</p>

                  <div className="p-2.5 rounded bg-[#071325] border border-slate-800 font-mono text-[11px] text-slate-400 flex flex-wrap gap-x-6 gap-y-1">
                    <span>SHA-256: {dup.file_hash.substring(0, 24)}...</span>
                    <span>Matched Application: {dup.matched_application_ref}</span>
                    <span>Matched Institution: {dup.matched_institution_name}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* SLIDE-OUT NODE INSPECTOR DRAWER                                           */}
      {/* ========================================================================= */}
      {selectedNode && (
        <div className="fixed inset-y-0 right-0 w-96 bg-[#071325] border-l border-[#1E3A5F] shadow-2xl z-50 p-6 flex flex-col justify-between overflow-y-auto text-xs animate-in slide-in-from-right">
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#1E3A5F]">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                <span className="font-bold text-sm text-white">TrustGraph Entity Inspector</span>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
              >
                ✕
              </button>
            </div>

            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold">
                  Tier {selectedNode.tier}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold">
                  {selectedNode.type}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 font-bold">
                  {selectedNode.status}
                </span>
              </div>
              <h3 className="text-base font-bold text-white mt-1">{selectedNode.label}</h3>
              <p className="text-[11px] font-mono text-slate-500 mt-0.5">ID: {selectedNode.id}</p>
            </div>

            {/* Metadata Table */}
            <div className="space-y-2 pt-2 border-t border-[#162C4E]">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Entity Metadata & Provenance Properties
              </div>
              <div className="bg-[#0B1E36] rounded-xl border border-[#1A365D] divide-y divide-[#162C4E]">
                {Object.entries(selectedNode.metadata || {}).map(([key, val]) => (
                  <div key={key} className="p-2.5 flex flex-col gap-0.5">
                    <span className="text-[10px] font-mono text-cyan-400 uppercase">{key}</span>
                    <span className="text-xs font-semibold text-slate-200 break-words">
                      {typeof val === "object" ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Connected Inbound & Outbound Edges */}
            <div className="space-y-2 pt-2 border-t border-[#162C4E]">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Direct Topological Connections
              </div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {data.edges
                  .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                  .map((e, idx) => {
                    const isSource = e.source === selectedNode.id;
                    const otherNodeId = isSource ? e.target : e.source;
                    const otherNode = data.nodes.find((n) => n.id === otherNodeId);

                    return (
                      <div
                        key={idx}
                        onClick={() => otherNode && setSelectedNode(otherNode)}
                        className="p-2 rounded-lg bg-[#0E2038] border border-slate-800 hover:border-cyan-400 cursor-pointer flex items-center justify-between transition-colors"
                      >
                        <div className="flex items-center gap-1.5 truncate">
                          <span className="font-mono text-cyan-300 font-bold text-[10px]">
                            {isSource ? `→ ${e.label} →` : `← ${e.label} ←`}
                          </span>
                          <span className="text-white font-medium truncate">
                            {otherNode?.label || otherNodeId}
                          </span>
                        </div>
                        <ChevronRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-[#1E3A5F]">
            <button
              onClick={() => setSelectedNode(null)}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-bold text-xs"
            >
              Close Inspector
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

