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
  const [viewMode, setViewMode] = useState<"model" | "plan">("model");
  
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
    geometryData,
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

          {/* ── Right Panel: 3D Viewer ── */}
          <section className="flex-1 relative min-h-0 overflow-hidden">
            {viewMode === "model" ? <ThreeJSViewer /> : <FloorPlanView floorPlan={geometryData?.floor_plan} />}

            <div className="absolute top-4 left-4 z-20 flex rounded-lg border border-slate-200/70 bg-white/85 p-1 shadow-lg backdrop-blur-md">
              <button
                onClick={() => setViewMode("model")}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[10px] font-semibold transition ${
                  viewMode === "model" ? "bg-[#7c93c3] text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <Cuboid className="h-3.5 w-3.5" />3D Model
              </button>
              <button
                onClick={() => {
                  setViewMode("plan");
                  setActiveProjection("orthographic_top");
                }}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[10px] font-semibold transition ${
                  viewMode === "plan" ? "bg-[#7c93c3] text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <Map className="h-3.5 w-3.5" />Floor Plan
              </button>
            </div>

            {/* Asset Library floating toggle button */}
            <button
              onClick={() => setAssetPaletteOpen(!isAssetPaletteOpen)}
              className={`absolute top-4 z-20 flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border shadow-lg backdrop-blur-md transition-all duration-200 ${
                isAssetPaletteOpen
                  ? "left-[284px] bg-[#7c93c3] text-white border-[#7c93c3]"
                  : "left-[190px] bg-white/80 text-slate-700 border-slate-200/60 hover:border-[#7c93c3] hover:text-[#7c93c3]"
              }`}
              style={{ top: isAssetPaletteOpen ? "auto" : undefined, bottom: isAssetPaletteOpen ? "auto" : undefined }}
            >
              {isAssetPaletteOpen
                ? <><X className="w-3.5 h-3.5" />Close Library</>
                : <><Package className="w-3.5 h-3.5" />Asset Library</>
              }
            </button>

            {/* Camera Projections overlay — top left */}
            <div className={`absolute top-4 z-10 bg-white/80 backdrop-blur-md border border-slate-200/60 rounded-xl p-3 shadow-lg w-60 transition-all duration-200 ${isAssetPaletteOpen ? "left-[300px]" : "left-[320px]"}`}>
              <div className="flex items-center gap-1.5 mb-2">
                <Eye className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Camera Projections</span>
              </div>
              <div className="space-y-1.5">
                <p className="text-[9px] text-slate-400 font-medium">Perspective (Interior)</p>
                <div className="grid grid-cols-3 gap-1">
                  {PROJECTIONS.slice(0,3).map(p => (
                    <button key={p.key} onClick={() => setActiveProjection(p.key)}
                      className={`py-1 rounded text-[9px] font-mono border transition ${
                        activeProjection === p.key
                          ? "bg-[#7c93c3]/20 border-[#7c93c3] text-slate-800 font-semibold"
                          : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700 hover:border-slate-300"
                      }`}>{p.label}</button>
                  ))}
                </div>
                <p className="text-[9px] text-slate-400 font-medium pt-0.5">Parallel Projections (Exterior)</p>
                <div className="grid grid-cols-3 gap-1">
                  {PROJECTIONS.slice(3,6).map(p => (
                    <button key={p.key} onClick={() => setActiveProjection(p.key)}
                      className={`py-1 rounded text-[9px] font-mono border transition ${
                        activeProjection === p.key
                          ? "bg-[#7c93c3]/20 border-[#7c93c3] text-slate-800 font-semibold"
                          : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700 hover:border-slate-300"
                      }`}>{p.label}</button>
                  ))}
                </div>
                <div className="grid grid-cols-3 gap-1">
                  {PROJECTIONS.slice(6).map(p => (
                    <button key={p.key} onClick={() => setActiveProjection(p.key)}
                      className={`py-1 rounded text-[9px] font-mono border transition ${
                        activeProjection === p.key
                          ? "bg-[#7c93c3]/20 border-[#7c93c3] text-slate-800 font-semibold"
                          : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700 hover:border-slate-300"
                      }`}>{p.label}</button>
                  ))}
                </div>
              </div>
            </div>

            {/* Component Filter — top right */}
            <div className="absolute top-4 right-4 z-10 bg-white/80 backdrop-blur-md border border-slate-200/60 rounded-xl p-3 shadow-lg w-52">
              <div className="flex items-center gap-1.5 mb-2">
                <Filter className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Component Filter</span>
              </div>
              <div className="grid grid-cols-2 gap-1">
                {COMPONENTS.map(g => (
                  <button key={g} onClick={() => setVisibleComponentGroup(g)}
                    className={`py-1.5 px-2 rounded text-[9px] font-medium border text-center transition ${
                      visibleComponentGroup === g
                        ? "bg-[#7c93c3]/20 border-[#7c93c3] text-slate-800 font-semibold"
                        : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700 hover:border-slate-300"
                    }`}>{g}</button>
                ))}
              </div>
            </div>

            {/* Walkthrough button */}
            {generatedGlbPath && (
              <button
                onClick={() => setWalkthrough(!isWalkthrough)}
                className={`absolute top-16 right-4 z-20 flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold shadow-lg transition-all ${
                  isWalkthrough
                    ? "bg-[#7c93c3] text-white"
                    : "bg-white/90 text-slate-700 border border-slate-200 hover:bg-[#7c93c3]/10"
                }`}
              >
                {isWalkthrough ? "🚶 Exit Walkthrough" : "🚶 Enter Walkthrough"}
              </button>
            )}
            {isWalkthrough && (
              <div className="absolute top-28 right-4 z-20 bg-black/70 text-white text-[10px] rounded-xl px-3 py-2 backdrop-blur pointer-events-none">
                <p className="font-bold mb-1">First Person Mode</p>
                <p>WASD / Arrow Keys — move</p>
                <p>Mouse — look around</p>
                <p>Shift — run</p>
                <p>Esc — exit</p>
              </div>
            )}
            {/* BOQ button */}
            {complianceData && (
              <button
                onClick={async () => {
                  const store = useStore.getState();
                  const g = store.geometryData;
                  const schema = (g as any)?.schema || {};
                  const params = new URLSearchParams({
                    floors: String(schema.floors || 3),
                    width: String(schema.width || 20),
                    depth: String(schema.depth || 15),
                    floor_height: String(schema.floor_height || 3.2),
                    building_type: schema.building_type || "apartment",
                  });
                  const res = await fetch(\`\${API_BASE}/api/cost-estimate?\${params}\`);
                  const data = await res.json();
                  setBoqData(data);
                  setShowBOQ(true);
                }}
                className="absolute bottom-16 right-4 z-20 flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold bg-white/90 text-slate-700 border border-slate-200 hover:bg-emerald-50 hover:border-emerald-300 shadow transition"
              >
                📋 Export BOQ / Cost
              </button>
            )}
            {/* BOQ Modal */}
            {showBOQ && boqData && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowBOQ(false)}>
                <div className="bg-white rounded-2xl shadow-2xl w-[480px] max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                    <div>
                      <h3 className="font-bold text-slate-800 text-sm">Bill of Quantities</h3>
                      <p className="text-[10px] text-slate-400">{boqData.building.total_area_m2} m² · {boqData.building.floors} floors</p>
                    </div>
                    <button onClick={() => setShowBOQ(false)} className="text-slate-400 hover:text-slate-600 text-lg">×</button>
                  </div>
                  <div className="px-6 py-4 space-y-4">
                    {/* Quantities */}
                    <div>
                      <p className="text-[10px] font-bold uppercase text-slate-500 mb-2">Material Quantities</p>
                      <div className="grid grid-cols-2 gap-1.5">
                        {Object.entries(boqData.quantities).map(([k,v]) => (
                          <div key={k} className="flex justify-between bg-slate-50 rounded-lg px-3 py-1.5 text-[10px]">
                            <span className="text-slate-500 capitalize">{k.replace(/_/g," ")}</span>
                            <span className="font-bold text-slate-700">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    {/* Cost breakdown */}
                    <div>
                      <p className="text-[10px] font-bold uppercase text-slate-500 mb-2">Cost Breakdown (INR)</p>
                      <div className="space-y-1">
                        {Object.entries(boqData.cost_breakdown_inr).map(([k,v]) => (
                          <div key={k} className="flex justify-between text-[10px] px-1">
                            <span className="text-slate-500">{k}</span>
                            <span className="font-medium text-slate-700">₹{Number(v).toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    {/* Totals */}
                    <div className="bg-[#7c93c3]/10 rounded-xl p-3 border border-[#7c93c3]/20">
                      <div className="flex justify-between text-sm font-bold text-slate-800 mb-1">
                        <span>Total Estimate</span>
                        <span>₹{Number(boqData.total_inr).toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between text-[10px] text-slate-500">
                        <span>USD equivalent</span>
                        <span>${Number(boqData.total_usd).toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between text-[10px] text-slate-500">
                        <span>Rate per sq.ft</span>
                        <span>₹{boqData.cost_per_sqft_inr}/sqft</span>
                      </div>
                    </div>
                    <p className="text-[9px] text-slate-400 text-center">{boqData.currency_note}</p>
                    <button onClick={() => window.print()}
                      className="w-full py-2 bg-[#7c93c3] text-white text-xs font-semibold rounded-xl hover:bg-[#8da3d3] transition">
                      🖨 Print / Export PDF
                    </button>
                  </div>
                </div>
              </div>
            )}
            {/* NBC Compliance panel — bottom right */}}
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
