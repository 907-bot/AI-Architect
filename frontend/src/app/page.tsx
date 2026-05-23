"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import AgentConsole from "@/components/AgentConsole";
import PromptBar from "@/components/PromptBar";
import ConfigPanel from "@/components/ConfigPanel";
import DroneCamera from "@/components/DroneCamera";
import SemanticSearch from "@/components/SemanticSearch";
import { 
  Box, Compass, CheckCircle2, AlertTriangle, 
  MapPin, Eye, Filter, Settings, Layers 
} from "lucide-react";
import { useStore, ProjectionType, ComponentGroupFilter } from "@/lib/store";

const ThreeJSViewer = dynamic(() => import("@/components/ThreeJSViewer"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-slate-50 text-slate-400 text-sm">
      Loading 3D Engine...
    </div>
  ),
});

const MapPicker = dynamic(() => import("@/components/MapPicker"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-slate-50 text-slate-400 text-xs">
      Loading Interactive Map...
    </div>
  ),
});

export default function WorkspacePage() {
  const [showConfig, setShowConfig] = useState(false);
  const [buildConfig, setBuildConfig] = useState({
    wallColor: "white", roofStyle: "gable", windowGlass: "clear",
    balcony: true, garage: true, pool: false, garden: true, floors: 2
  });
  const { 
    plotLat, plotLng, plotWidth, plotDepth, setPlotData,
    activeProjection, setActiveProjection,
    visibleComponentGroup, setVisibleComponentGroup,
    complianceData
  } = useStore();

  // Handle config build events from ConfigPanel
  useState(() => {
    const handler = (e: any) => {
      const promptBar = document.querySelector('input') as HTMLInputElement;
      if (promptBar) {
        promptBar.value = e.detail;
        promptBar.dispatchEvent(new Event('change', { bubbles: true }));
      }
    };
    window.addEventListener('build-config', handler);
    return () => window.removeEventListener('build-config', handler);
  }, []);

  return (
    <main className="relative flex flex-col h-screen w-screen bg-[#f9f9fb] text-slate-800 overflow-hidden grid-bg">
      {/* ── Header ── */}
      <header className="relative flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-white/70 backdrop-blur-md z-20">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-[#7c93c3]/15 border border-[#7c93c3]/30">
            <Box className="w-4 h-4 text-[#7c93c3]" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-wider text-slate-800 font-outfit uppercase flex items-center gap-1.5">
              AI Architect <span className="text-[10px] bg-[#7c93c3]/20 text-[#5a6e9c] border border-[#7c93c3]/35 px-1.5 py-0.5 rounded font-mono font-normal">v1.1</span>
            </h1>
            <p className="text-[10px] text-slate-400 font-sans">Indian NBC Zoning & Parallel Projections Enabled</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-[10px] text-slate-500 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-full">
            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping" />
            NBC Auditor Active
          </div>
        </div>
      </header>

      {/* ── Main Workspace Split Layout ── */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Left Side Panel: Agent Stream & Controls */}
        <aside className="w-80 border-r border-slate-100 bg-white/30 p-4 flex flex-col gap-4 overflow-y-auto z-10">
          
          {/* Interactive Map Selector */}
          <MapPicker />

          {/* Plot Dimensions */}
          <div className="glass-panel p-4 rounded-xl space-y-3">
            <div className="flex items-center gap-2 text-slate-700">
              <Settings className="w-4 h-4 text-slate-500" />
              <h3 className="text-xs font-semibold tracking-wide uppercase font-outfit">Plot Dimensions</h3>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div>
                <label className="text-slate-400">Width (m)</label>
                <input 
                  type="number" 
                  value={plotWidth} 
                  onChange={e => setPlotData(plotLat, plotLng, parseFloat(e.target.value) || 20.0, plotDepth)} 
                  className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-800"
                />
              </div>
              <div>
                <label className="text-slate-400">Depth (m)</label>
                <input 
                  type="number" 
                  value={plotDepth} 
                  onChange={e => setPlotData(plotLat, plotLng, plotWidth, parseFloat(e.target.value) || 30.0)} 
                  className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-800"
                />
              </div>
            </div>
          </div>

          <AgentConsole />
          
          {/* Exterior Configuration Panel */}
          <div className="mt-2">
            <button onClick={() => setShowConfig(!showConfig)}
              className="w-full py-2 px-3 bg-slate-100 rounded-lg text-xs font-medium text-slate-600 flex items-center justify-between">
              <span>Customize Exterior</span>
              <span className="text-xs">{showConfig ? "−" : "+"}</span>
            </button>
            {showConfig && <div className="mt-2"><ConfigPanel config={buildConfig} setConfig={setBuildConfig} /></div>}
          </div>
          <DroneCamera />
          <SemanticSearch />
        </aside>

        {/* Center/Right Panel: Canvas View */}
        <section className="flex-1 relative h-full w-full">
          <ThreeJSViewer />

          {/* Projection Controls Overlay */}
          <div className="absolute top-4 left-4 glass-panel p-3 rounded-xl flex flex-col gap-2 z-10 w-64">
            <div className="flex items-center gap-1.5 text-slate-700 mb-1">
              <Eye className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-[10px] font-semibold uppercase tracking-wider font-outfit">Camera Projections</span>
            </div>
            
            {/* Perspective selections */}
            <div className="space-y-1">
              <div className="text-[9px] text-slate-400 font-medium">Perspective (Interior)</div>
              <div className="grid grid-cols-3 gap-1">
                {(["perspective_1p", "perspective_2p", "perspective_3p"] as ProjectionType[]).map((p) => (
                  <button
                    key={p}
                    onClick={() => setActiveProjection(p)}
                    className={`py-1 rounded text-[9px] font-mono border transition ${
                      activeProjection === p 
                        ? "bg-[#7c93c3]/20 border-[#7c93c3] text-slate-800 font-semibold" 
                        : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    {p === "perspective_1p" ? "1-Point" : p === "perspective_2p" ? "2-Point" : "3-Point"}
                  </button>
                ))}
              </div>
            </div>

            {/* Parallel / Orthographic selections */}
            <div className="space-y-1 mt-1">
              <div className="text-[9px] text-slate-400 font-medium">Parallel Projections (Exterior)</div>
              <div className="grid grid-cols-3 gap-1">
                {(["orthographic_top", "orthographic_front", "orthographic_side"] as ProjectionType[]).map((p) => (
                  <button
                    key={p}
                    onClick={() => setActiveProjection(p)}
                    className={`py-1 rounded text-[9px] font-mono border transition ${
                      activeProjection === p 
                        ? "bg-[#7c93c3]/20 border-[#7c93c3] text-slate-800 font-semibold" 
                        : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    {p.split("_")[1].toUpperCase()}
                  </button>
                ))}
              </div>
              <div className="grid grid-cols-3 gap-1">
                {(["isometric", "oblique_cavalier", "oblique_cabinet"] as ProjectionType[]).map((p) => (
                  <button
                    key={p}
                    onClick={() => setActiveProjection(p)}
                    className={`py-1 rounded text-[9px] font-mono border transition ${
                      activeProjection === p 
                        ? "bg-[#7c93c3]/20 border-[#7c93c3] text-slate-800 font-semibold" 
                        : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    {p === "isometric" ? "Isometric" : p === "oblique_cavalier" ? "Cavalier" : "Cabinet"}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Component Visibility Overlay */}
          <div className="absolute top-4 right-4 glass-panel p-3 rounded-xl flex flex-col gap-2 z-10 w-52">
            <div className="flex items-center gap-1.5 text-slate-700 mb-1">
              <Filter className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-[10px] font-semibold uppercase tracking-wider font-outfit">Component Filter</span>
            </div>
            <div className="grid grid-cols-2 gap-1.5 text-[9px]">
              {(["All", "Foundation", "Floor Slabs", "Walls", "Windows", "Roof"] as ComponentGroupFilter[]).map((group) => (
                <button
                  key={group}
                  onClick={() => setVisibleComponentGroup(group)}
                  className={`py-1 px-2 rounded font-medium border text-center transition ${
                    visibleComponentGroup === group
                      ? "bg-[#7c93c3]/20 border-[#7c93c3] text-slate-800 font-semibold"
                      : "bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-700"
                  }`}
                >
                  {group}
                </button>
              ))}
            </div>
          </div>

          {/* Indian NBC Zoning Audit Report Panel */}
          {complianceData && (
            <div className="absolute bottom-24 right-4 glass-panel p-4 rounded-xl w-80 z-10 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                <div className="flex items-center gap-1.5">
                  <Layers className="w-4 h-4 text-slate-500" />
                  <span className="text-xs font-semibold uppercase tracking-wider font-outfit text-slate-800">NBC 2016 Zoning Audit</span>
                </div>
                {complianceData.compliant ? (
                  <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                    <CheckCircle2 className="w-3 h-3" />
                    COMPLIANT
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-[10px] font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-full">
                    <AlertTriangle className="w-3 h-3" />
                    NON-COMPLIANT
                  </span>
                )}
              </div>

              {/* FAR & Coverage Metrics */}
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="p-2 rounded bg-slate-50 border border-slate-100">
                  <div className="text-slate-400">Floor Area Ratio (FAR)</div>
                  <div className="text-xs font-bold text-slate-700 mt-0.5">
                    {complianceData.actual_far ?? "N/A"} <span className="text-slate-400 font-normal">/ {complianceData.allowed_far ?? "2.5"}</span>
                  </div>
                </div>
                <div className="p-2 rounded bg-slate-50 border border-slate-100">
                  <div className="text-slate-400">Ground Coverage</div>
                  <div className="text-xs font-bold text-slate-700 mt-0.5">
                    {complianceData.actual_coverage_pct ?? "N/A"}% <span className="text-slate-400 font-normal">/ {complianceData.allowed_coverage_pct ?? "60"}%</span>
                  </div>
                </div>
              </div>

              {/* Issues/Compliance Alert checklist */}
              {complianceData.issues.length > 0 && (
                <div className="space-y-1">
                  <div className="text-[9px] text-slate-400 font-semibold uppercase tracking-wider">Discrepancy Checklist</div>
                  <div className="space-y-1 max-h-24 overflow-y-auto">
                    {complianceData.issues.map((issue, idx) => (
                      <div key={idx} className="flex gap-1.5 text-[9px] text-rose-700 bg-rose-50 p-1.5 rounded border border-rose-100">
                        <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                        <span>{issue}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Vastu Shastra Guidelines */}
              {complianceData.vastu_suggestions && complianceData.vastu_suggestions.length > 0 && (
                <div className="space-y-1 border-t border-slate-100 pt-2">
                  <div className="text-[9px] text-slate-400 font-semibold uppercase tracking-wider">Vastu Shastra Suggestions</div>
                  <ul className="list-disc pl-3 text-[9px] text-emerald-700 space-y-0.5">
                    {complianceData.vastu_suggestions.map((tip, idx) => (
                      <li key={idx}>{tip}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Bottom Floating prompt input panel */}
          <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 w-full max-w-2xl px-4 z-10">
            <PromptBar />
          </div>
        </section>
      </div>
    </main>
  );
}
