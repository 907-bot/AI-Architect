"use client";
import UnrealExport from "@/components/UnrealExport";
import MapView from "@/components/MapView";
import GovernmentNorms from "@/components/GovernmentNorms";
import StylePicker from "@/components/StylePicker";

import React, { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import ChatPanel from "@/components/ChatPanel";
import PromptBar from "@/components/PromptBar";
import ConfigPanel from "@/components/ConfigPanel";
import DroneCamera from "@/components/DroneCamera";
import BuildingLoader from "@/components/BuildingLoader";
import AssetPalette from "@/components/AssetPalette";
import FloorPlanView from "@/components/FloorPlanView";
import {
  Box, Eye, Filter, Layers, ChevronDown, ChevronUp, Cuboid, Map,
  CheckCircle2, AlertTriangle, Settings2, Package, X,
  Cpu, Cog
} from "lucide-react";
import { useStore, ProjectionType, ComponentGroupFilter } from "@/lib/store";
import { API_BASE, unwrapApiResponse } from "@/lib/mvpScene";

const ThreeJSViewer = dynamic(() => import("@/components/ThreeJSViewer"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-[#dbeafe]">
      <div className="flex flex-col items-center gap-3 text-slate-400">
        <div className="w-8 h-8 border-2 border-[#7c93c3] border-t-transparent rounded-full animate-spin" />
        <span className="text-xs">Loading 3D Engine…</span>
      </div>
    </div>
  ),
});

const MapPicker = dynamic(() => import("@/components/MapPicker"), { ssr: false });

// ─── Projection selector ──────────────────────────────────────────────────────

const PROJECTIONS: { key: ProjectionType; label: string }[] = [
  { key: "perspective_1p", label: "1-Point" },
  { key: "perspective_2p", label: "2-Point" },
  { key: "perspective_3p", label: "3-Point" },
  { key: "orthographic_top", label: "TOP" },
  { key: "orthographic_front", label: "FRONT" },
  { key: "orthographic_side", label: "SIDE" },
  { key: "isometric", label: "Isometric" },
  { key: "oblique_cavalier", label: "Cavalier" },
  { key: "oblique_cabinet", label: "Cabinet" },
];

const COMPONENTS: ComponentGroupFilter[] = ["All", "Foundation", "Floor Slabs", "Walls", "Doors", "Windows", "Roof", "Interior"];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function WorkspacePage() {
  const [buildConfig, setBuildConfig] = useState({
    wallColor: "white", roofStyle: "gable", windowGlass: "clear",
    balcony: true, garage: true, pool: false, garden: true, floors: 2,
  });
  const [showConfig, setShowConfig] = useState(false);
  const [showMap, setShowMap] = useState(false);
  const [viewMode, setViewMode] = useState<"model" | "plan" | "unreal">("model");
  
  // Connection status
  const [blenderStatus, setBlenderStatus] = useState<{available: boolean; version?: string} | null>(null);
  const [ollamaStatus, setOllamaStatus] = useState<{available: boolean; model?: string} | null>(null);
  const [redisStatus, setRedisStatus] = useState<{available: boolean; backend?: string} | null>(null);
  const [mcpStatus, setMcpStatus] = useState<{available: boolean} | null>(null);

  const {
    activeProjection, setActiveProjection,
    visibleComponentGroup, setVisibleComponentGroup,
    complianceData, isGenerating,
    plotLat, plotLng, plotWidth, plotDepth, setPlotData,
    isAssetPaletteOpen, setAssetPaletteOpen,
    geometryData, generatedGlbPath,
  } = useStore();
  const isWalkthrough   = useStore((s) => s.isWalkthrough);
  const setWalkthrough  = useStore((s) => s.setWalkthrough);
  const selectedRoomId  = useStore((s) => s.selectedRoomId);
  const [showBOQ, setShowBOQ] = React.useState(false);
  const [boqData, setBoqData] = React.useState<any>(null);
  const [activeStyle, setActiveStyle] = React.useState("modern");
  const booted = useRef(false);

  useEffect(() => {
    if (booted.current) return;
    booted.current = true;

    // Clear any existing state - start with empty scene
    const store = useStore.getState();
    store.setGeneratedGlbPath(null);
    
    // Check stack status
    fetch(`${API_BASE}/api/stack-status`)
      .then(res => res.json())
      .then(raw => {
        const data = unwrapApiResponse(raw);
        const blender = data.blender || {};
        const ollama = data.ollama || {};
        const redis = data.redis || {};
        const blenderMcp = data.blender_mcp || {};

        setBlenderStatus({ available: !!blender.available, version: blender.version });
        setOllamaStatus({ available: !!ollama.available, model: ollama.model });
        setRedisStatus({ available: !!redis.available, backend: redis.backend });
        setMcpStatus({ available: !!blenderMcp.available });

        useStore.getState().addAgentLog({
          agent: "system",
          message: blender.available 
            ? `✓ Blender: ${blender.version || 'Available'}` 
            : "✗ Blender: Not available (install Blender or Docker)",
        });
        useStore.getState().addAgentLog({
          agent: "system",
          message: ollama.available 
            ? `✓ Ollama: ${ollama.model || 'llama3.1'}` 
            : "✗ Ollama: Not available (run: ollama serve && ollama pull llama3.1)",
        });
        useStore.getState().addAgentLog({
          agent: "system",
          message: redis.available 
            ? `✓ Queue: ${redis.backend || 'redis'}` 
            : "✗ Redis: Not reachable; queue may fall back locally",
        });
        useStore.getState().addAgentLog({
          agent: "system",
          message: blenderMcp.available 
            ? "✓ Blender MCP: HTTP server reachable" 
            : "✗ Blender MCP: Start server on port 8765 when MCP tools are needed",
        });
      })
      .catch(() => {
        setBlenderStatus({ available: false });
        setOllamaStatus({ available: false });
        setRedisStatus({ available: false });
        setMcpStatus({ available: false });
        useStore.getState().addAgentLog({
          agent: "system",
          message: `✗ Backend not reachable at ${API_BASE}. If the API is running, restart it after pulling latest CORS fixes, then open this app at the port shown in the terminal (e.g. http://localhost:3002).`,
        });
      });
  }, []);

  return (
    <>
      <BuildingLoader isLoading={isGenerating} />

      <main className="flex flex-col h-screen w-screen bg-[#f5f7fb] overflow-hidden">

        {/* ── Header ── */}
        <header className="flex items-center justify-between px-5 py-3 bg-white border-b border-slate-100 z-20 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#7c93c3]/15 border border-[#7c93c3]/30 flex items-center justify-center">
              <Box className="w-4 h-4 text-[#7c93c3]" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-wide text-slate-800 font-outfit uppercase flex items-center gap-1.5">
                AI Architect
                <span className="text-[10px] bg-[#7c93c3]/15 text-[#5a6e9c] border border-[#7c93c3]/30 px-1.5 py-0.5 rounded font-mono font-normal">v1.1</span>
              </h1>
              <p className="text-[10px] text-slate-400">Indian NBC Zoning & Parallel Projections Enabled</p>
            </div>
          </div>
          
          {/* Status indicators */}
          <div className="flex items-center gap-3">
            {/* Ollama Status */}
            <div className={`flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full border ${
              ollamaStatus?.available 
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700' 
                : 'bg-amber-50 border-amber-200 text-amber-700'
            }`}>
              <Cpu className="w-3 h-3" />
              <span>Ollama: {ollamaStatus?.available ? '✓' : '✗'}</span>
            </div>
            
            {/* Blender Status */}
            <div className={`flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full border ${
              blenderStatus?.available 
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700' 
                : 'bg-amber-50 border-amber-200 text-amber-700'
            }`}>
              <Cog className="w-3 h-3" />
              <span>Blender: {blenderStatus?.available ? '✓' : '✗'}</span>
            </div>

            <div className={`flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full border ${
              redisStatus?.available
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : 'bg-amber-50 border-amber-200 text-amber-700'
            }`}>
              <Layers className="w-3 h-3" />
              <span>Redis: {redisStatus?.available ? '✓' : '✗'}</span>
            </div>

            <div className={`flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full border ${
              mcpStatus?.available
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : 'bg-amber-50 border-amber-200 text-amber-700'
            }`}>
              <Package className="w-3 h-3" />
              <span>MCP: {mcpStatus?.available ? '✓' : '✗'}</span>
            </div>
          </div>
        </header>

        {/* ── Body ── */}
        <div className="flex flex-1 min-h-0 overflow-hidden relative">

          {/* ── Left Panel: Chat ── */}
          <aside className="w-[340px] flex flex-col bg-white border-r border-slate-100 min-h-0 z-10">
            {/* Chat messages */}
            <ChatPanel />

            {/* Config accordion */}
            <div className="border-t border-slate-100">
              <button
                onClick={() => setShowConfig(v => !v)}
                className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
              >
                <span className="flex items-center gap-2"><Settings2 className="w-3.5 h-3.5" />Customize Exterior</span>
                {showConfig ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
              {showConfig && (
                <div className="px-3 pb-3">
                  <ConfigPanel config={buildConfig} setConfig={setBuildConfig} />
                </div>
              )}
            </div>

            {/* Map accordion */}
            <div className="border-t border-slate-100">
              <button
                onClick={() => setShowMap(v => !v)}
                className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition"
              >
                <span className="flex items-center gap-2">📍 Plot Location & Dimensions</span>
                {showMap ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
              {showMap && (
                <div className="px-3 pb-3 space-y-2">
                  <MapView />
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <label className="text-slate-400 block mb-1">Width (m)</label>
                      <input type="number" value={plotWidth}
                        onChange={e => setPlotData(plotLat, plotLng, parseFloat(e.target.value)||20, plotDepth)}
                        className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-800 outline-none focus:border-[#7c93c3]" />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Depth (m)</label>
                      <input type="number" value={plotDepth}
                        onChange={e => setPlotData(plotLat, plotLng, plotWidth, parseFloat(e.target.value)||30)}
                        className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-800 outline-none focus:border-[#7c93c3]" />
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Drone camera */}
            <div className="border-t border-slate-100 px-3 py-2">
              <DroneCamera />
            </div>

            {/* Prompt input bar */}
            <div className="border-t border-slate-100 px-3 py-3 bg-slate-50/60">
              <PromptBar buildConfig={buildConfig} />
            </div>
          </aside>

          {/* ── Asset Palette — floating overlay over 3D viewer ── */}
          {isAssetPaletteOpen && (
            <div className="absolute left-[340px] top-0 bottom-0 z-30 shadow-2xl">
              <AssetPalette onClose={() => setAssetPaletteOpen(false)} />
            </div>
          )}

          {/* ── Right Panel ── */}
          <section className="flex-1 relative min-h-0 overflow-hidden flex flex-col">

            {/* ── Toolbar row — NO overlapping ── */}
            <div className="flex items-center gap-2 px-3 py-2 bg-white border-b border-slate-100 z-20 flex-shrink-0 flex-wrap">

              {/* View mode tabs */}
              <div className="flex rounded-lg border border-slate-200/70 bg-slate-50 p-0.5">
                <button onClick={() => setViewMode("model")}
                  className={`flex items-center gap-1.5 rounded px-2.5 py-1 text-[10px] font-semibold transition ${viewMode==="model"?"bg-white shadow text-slate-800 border border-slate-200":"text-slate-500 hover:text-slate-700"}`}>
                  <Cuboid className="h-3 w-3" />3D Model
                </button>
                <button onClick={() => { setViewMode("plan"); setActiveProjection("orthographic_top"); }}
                  className={`flex items-center gap-1.5 rounded px-2.5 py-1 text-[10px] font-semibold transition ${viewMode==="plan"?"bg-white shadow text-slate-800 border border-slate-200":"text-slate-500 hover:text-slate-700"}`}>
                  <Map className="h-3 w-3" />Floor Plan
                </button>
                <button onClick={() => setViewMode("unreal")}
                  className={`flex items-center gap-1.5 rounded px-2.5 py-1 text-[10px] font-semibold transition ${viewMode==="unreal"?"bg-white shadow text-slate-800 border border-slate-200":"text-slate-500 hover:text-slate-700"}`}>
                  🎮 Unreal
                </button>
              </div>

              {/* Divider */}
              <div className="h-5 w-px bg-slate-200" />

              {/* Component filter — only in 3D mode */}
              {viewMode === "model" && (
                <select value={visibleComponentGroup}
                  onChange={e => setVisibleComponentGroup(e.target.value as any)}
                  className="text-[10px] border border-slate-200 rounded-lg px-2 py-1.5 bg-white text-slate-600 font-medium cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#7c93c3]">
                  {COMPONENTS.map(g => <option key={g} value={g}>{g}</option>)}
                </select>
              )}

              {/* Camera projection — only in 3D mode */}
              {viewMode === "model" && (
                <select value={activeProjection}
                  onChange={e => setActiveProjection(e.target.value as any)}
                  className="text-[10px] border border-slate-200 rounded-lg px-2 py-1.5 bg-white text-slate-600 font-medium cursor-pointer focus:outline-none focus:ring-1 focus:ring-[#7c93c3]">
                  {PROJECTIONS.map(p => <option key={p.key} value={p.key}>{p.label}</option>)}
                </select>
              )}

              {/* Walkthrough — only when GLB exists in 3D mode */}
              {viewMode === "model" && generatedGlbPath && (
                <button onClick={() => setWalkthrough(!isWalkthrough)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold transition border ${
                    isWalkthrough
                      ? "bg-[#7c93c3] text-white border-[#7c93c3]"
                      : "bg-white text-slate-600 border-slate-200 hover:border-[#7c93c3] hover:text-[#7c93c3]"
                  }`}>
                  🚶 {isWalkthrough ? "Exit Walk" : "Walkthrough"}
                </button>
              )}

              {/* Asset Library button */}
              <button onClick={() => setAssetPaletteOpen(!isAssetPaletteOpen)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold transition border ${
                  isAssetPaletteOpen
                    ? "bg-[#7c93c3] text-white border-[#7c93c3]"
                    : "bg-white text-slate-600 border-slate-200 hover:border-[#7c93c3] hover:text-[#7c93c3]"
                }`}>
                <Package className="w-3 h-3" />{isAssetPaletteOpen ? "Close" : "Assets"}
              </button>

              {/* BOQ button */}
              {complianceData && (
                <button onClick={async () => {
                  const schema = (useStore.getState().geometryData as any)?.schema || {};
                  const params = new URLSearchParams({
                    floors: String(schema.floors||3), width: String(schema.width||20),
                    depth: String(schema.depth||15), floor_height: String(schema.floor_height||3.2),
                    building_type: schema.building_type||"apartment",
                  });
                  const res = await fetch(`${API_BASE}/api/cost-estimate?${params}`);
                  setBoqData(await res.json()); setShowBOQ(true);
                }}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-semibold border bg-white text-slate-600 border-slate-200 hover:border-emerald-400 hover:text-emerald-600 transition ml-auto">
                  📋 BOQ
                </button>
              )}
            </div>

            {/* ── Asset palette slide-in — BELOW toolbar, not over viewer ── */}
            {isAssetPaletteOpen && (
              <div className="absolute left-0 top-[41px] bottom-0 z-30 shadow-2xl w-72">
                <AssetPalette onClose={() => setAssetPaletteOpen(false)} />
              </div>
            )}

            {/* ── Main view area ── */}
            <div className="flex-1 relative min-h-0">
              {viewMode === "model"  && <ThreeJSViewer />}
              {viewMode === "plan"   && <FloorPlanView floorPlan={geometryData?.floor_plan} />}
              {viewMode === "unreal" && <UnrealExport />}

              {/* Compass — only in 3D model mode */}
              {viewMode === "model" && (
                <div className="absolute bottom-4 right-4 z-10 pointer-events-none">
                  <svg width="68" height="68" viewBox="0 0 68 68" className="drop-shadow-lg">
                    <circle cx="34" cy="34" r="32" fill="white" fillOpacity="0.88" stroke="#e2e8f0" strokeWidth="1.5"/>
                    {/* N — red */}
                    <polygon points="34,6 30,34 34,30 38,34" fill="#ef4444"/>
                    {/* S — dark */}
                    <polygon points="34,62 30,34 34,38 38,34" fill="#334155"/>
                    {/* W */}
                    <polygon points="6,34 34,30 30,34 34,38" fill="#94a3b8"/>
                    {/* E */}
                    <polygon points="62,34 34,30 38,34 34,38" fill="#94a3b8"/>
                    <circle cx="34" cy="34" r="3.5" fill="#1e293b"/>
                    <text x="34" y="4"  textAnchor="middle" fontSize="9" fontWeight="800" fill="#ef4444" fontFamily="system-ui">N</text>
                    <text x="34" y="66" textAnchor="middle" fontSize="9" fontWeight="700" fill="#64748b" fontFamily="system-ui">S</text>
                    <text x="3"  y="37" textAnchor="middle" fontSize="9" fontWeight="700" fill="#64748b" fontFamily="system-ui">W</text>
                    <text x="65" y="37" textAnchor="middle" fontSize="9" fontWeight="700" fill="#64748b" fontFamily="system-ui">E</text>
                  </svg>
                </div>
              )}

            </div>

            {/* NBC Compliance panel — bottom right */}            {/* NBC Compliance panel — bottom right */}
            {complianceData && (
              <div className="absolute bottom-6 right-4 z-10 bg-white/90 backdrop-blur-md border border-slate-200/60 rounded-xl p-4 shadow-lg w-80">
                <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
                  <div className="flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700">NBC 2016 Zoning Audit</span>
                  </div>
                  {complianceData.compliant ? (
                    <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                      <CheckCircle2 className="w-3 h-3" />COMPLIANT
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-full">
                      <AlertTriangle className="w-3 h-3" />NON-COMPLIANT
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2 text-[10px] mb-3">
                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="text-slate-400 mb-0.5">Floor Area Ratio (FAR)</div>
                    <div className="font-bold text-slate-700">
                      {complianceData.actual_far ?? "—"} <span className="text-slate-400 font-normal">/ {complianceData.allowed_far ?? 2.5}</span>
                    </div>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="text-slate-400 mb-0.5">Ground Coverage</div>
                    <div className="font-bold text-slate-700">
                      {complianceData.actual_coverage_pct ?? "—"}% <span className="text-slate-400 font-normal">/ {complianceData.allowed_coverage_pct ?? 60}%</span>
                    </div>
                  </div>
                </div>
                {complianceData.issues.length > 0 && (
                  <div className="space-y-1 mb-2">
                    {(complianceData?.issues || []).map((issue, i) => (
                      <div key={i} className="flex gap-1.5 text-[9px] text-rose-700 bg-rose-50 p-1.5 rounded-lg border border-rose-100">
                        <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5" />{issue}
                      </div>
                    ))}
                  </div>
                )}
                {(complianceData?.vastu_suggestions?.length ?? 0) > 0 && (
                  <div className="border-t border-slate-100 pt-2">
                    <div className="text-[9px] font-semibold uppercase tracking-wider text-slate-400 mb-1">Vastu Shastra Suggestions</div>
                    <ul className="space-y-0.5 list-disc pl-3 text-[9px] text-emerald-700">
                      {(complianceData?.vastu_suggestions || []).map((s,i) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </main>
    </>
  );
}
