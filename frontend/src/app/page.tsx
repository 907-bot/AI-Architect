"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import ChatPanel from "@/components/ChatPanel";
import PromptBar from "@/components/PromptBar";
import ConfigPanel from "@/components/ConfigPanel";
import DroneCamera from "@/components/DroneCamera";
import BuildingLoader from "@/components/BuildingLoader";
import AssetPalette from "@/components/AssetPalette";
import {
  Box, Eye, Filter, Layers, ChevronDown, ChevronUp,
  CheckCircle2, AlertTriangle, Settings2, Package, X,
} from "lucide-react";
import { useStore, ProjectionType, ComponentGroupFilter } from "@/lib/store";

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

const COMPONENTS: ComponentGroupFilter[] = ["All", "Foundation", "Floor Slabs", "Walls", "Windows", "Roof"];

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function WorkspacePage() {
  const [buildConfig, setBuildConfig] = useState({
    wallColor: "white", roofStyle: "gable", windowGlass: "clear",
    balcony: true, garage: true, pool: false, garden: true, floors: 2,
  });
  const [showConfig, setShowConfig] = useState(false);
  const [showMap, setShowMap] = useState(false);

  const {
    activeProjection, setActiveProjection,
    visibleComponentGroup, setVisibleComponentGroup,
    complianceData, isGenerating,
    plotLat, plotLng, plotWidth, plotDepth, setPlotData,
    isAssetPaletteOpen, setAssetPaletteOpen,
  } = useStore();

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
          <div className="flex items-center gap-2 text-[10px] text-slate-500 bg-emerald-50 border border-emerald-200 px-2.5 py-1 rounded-full">
            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
            NBC Auditor Active
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
                  <MapPicker />
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
            <ThreeJSViewer />

            {/* Asset Library floating toggle button */}
            <button
              onClick={() => setAssetPaletteOpen(!isAssetPaletteOpen)}
              className={`absolute top-4 z-20 flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border shadow-lg backdrop-blur-md transition-all duration-200 ${
                isAssetPaletteOpen
                  ? "left-[284px] bg-[#7c93c3] text-white border-[#7c93c3]"
                  : "left-4 bg-white/80 text-slate-700 border-slate-200/60 hover:border-[#7c93c3] hover:text-[#7c93c3]"
              }`}
              style={{ top: isAssetPaletteOpen ? "auto" : undefined, bottom: isAssetPaletteOpen ? "auto" : undefined }}
            >
              {isAssetPaletteOpen
                ? <><X className="w-3.5 h-3.5" />Close Library</>
                : <><Package className="w-3.5 h-3.5" />Asset Library</>
              }
            </button>

            {/* Camera Projections overlay — top left */}
            <div className={`absolute top-4 z-10 bg-white/80 backdrop-blur-md border border-slate-200/60 rounded-xl p-3 shadow-lg w-60 transition-all duration-200 ${isAssetPaletteOpen ? "left-[300px]" : "left-[140px]"}`}>
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

            {/* NBC Compliance panel — bottom right */}
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
