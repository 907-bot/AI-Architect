"use client";
import React, { useState } from "react";
import { useStore } from "@/lib/store";
import { API_BASE } from "@/lib/mvpScene";
import {
  Download, CheckCircle, AlertCircle, Loader2,
  Zap, Box, Camera, Cpu, ChevronDown, ChevronUp
} from "lucide-react";

const STEPS = [
  { icon:"🔌", label:"Enable Plugins",   desc:"Python Script, Interchange, Nanite, Lumen" },
  { icon:"⚙️",  label:"Project Settings", desc:"Lumen GI · Virtual Shadow Maps · Nanite on" },
  { icon:"📦",  label:"Download Package", desc:"GLB + UE5 automation script + README" },
  { icon:"🐍",  label:"Run Script",       desc:"Tools → Execute Python Script → ue5_setup.py" },
  { icon:"🏗️",  label:"Building Live",   desc:"Nanite meshes + Lumen GI + Sky Atmosphere" },
];

const FEATURES = [
  { icon:<Zap  className="w-4 h-4 text-yellow-500" />, label:"Lumen GI",          desc:"Real-time global illumination, no lightmaps" },
  { icon:<Box  className="w-4 h-4 text-blue-500"   />, label:"Nanite",            desc:"Infinite polygon detail, zero LOD pop-in" },
  { icon:<Camera className="w-4 h-4 text-purple-500"/>, label:"Path Tracing",     desc:"Hollywood-quality photorealistic stills" },
  { icon:<Cpu  className="w-4 h-4 text-emerald-500"/>, label:"Virtual Shadow Maps",desc:"Crisp ray-traced shadows at all distances" },
];

const CONSOLE_CMDS = [
  { label:"Enable Path Tracer",   cmd:'r.PathTracing 1' },
  { label:"4096 SPP render",      cmd:'r.PathTracing.SamplesPerPixel 4096' },
  { label:"16 light bounces",     cmd:'r.PathTracing.MaxBounces 16' },
  { label:"Virtual Shadow Maps",  cmd:'r.Shadow.Virtual.Enable 1' },
  { label:"Lumen reflections",    cmd:'r.Lumen.Reflections.ScreenTraces 1' },
  { label:"Ray-traced glass",     cmd:'r.RayTracing.Reflections 1' },
];

export default function UnrealExport() {
  const generatedGlbPath = useStore(s => s.generatedGlbPath);
  const geometryData     = useStore(s => s.geometryData);
  const [downloading, setDownloading]   = useState(false);
  const [downloaded,  setDownloaded]    = useState(false);
  const [showCmds,    setShowCmds]      = useState(false);
  const [copiedCmd,   setCopiedCmd]     = useState<string | null>(null);
  const [checklist,   setChecklist]     = useState<any | null>(null);
  const [loadingCL,   setLoadingCL]     = useState(false);

  const glbFilename  = generatedGlbPath?.split("/").pop() ?? "";
  const schema       = (geometryData as any)?.schema ?? {};
  const style        = schema.style ?? "modern";
  const floors       = schema.floors ?? 3;
  const hasBuilding  = !!generatedGlbPath;

  const handleDownload = async () => {
    if (!hasBuilding) return;
    setDownloading(true);
    try {
      const url  = `${API_BASE}/api/export-unreal?glb_filename=${encodeURIComponent(glbFilename)}`;
      const resp = await fetch(url);
      if (!resp.ok) throw new Error("Export failed");
      const blob = await resp.blob();
      const link = document.createElement("a");
      link.href  = URL.createObjectURL(blob);
      link.download = `AIArchitect_UE5_${glbFilename.replace(".glb","")}.zip`;
      link.click();
      URL.revokeObjectURL(link.href);
      setDownloaded(true);
    } catch (err) {
      console.error("UE5 export error:", err);
    }
    setDownloading(false);
  };

  const loadChecklist = async () => {
    if (checklist) return;
    setLoadingCL(true);
    try {
      const r = await fetch(`${API_BASE}/api/unreal-checklist`);
      setChecklist(await r.json());
    } catch { /* noop */ }
    setLoadingCL(false);
  };

  const copyCmd = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedCmd(cmd);
    setTimeout(() => setCopiedCmd(null), 1500);
  };

  return (
    <div className="absolute inset-0 overflow-y-auto bg-[#0d0d14] text-white">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-[#0d0d14]/95 backdrop-blur border-b border-white/10 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#7c93c3]/20 flex items-center justify-center">
            <span className="text-lg">🎮</span>
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Unreal Engine 5</h2>
            <p className="text-[9px] text-white/40">Nanite · Lumen GI · Path Tracing</p>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-4">

        {/* Building summary */}
        {hasBuilding ? (
          <div className="rounded-xl bg-white/5 border border-white/10 p-3">
            <p className="text-[9px] text-white/40 uppercase tracking-wider mb-2">Ready to Export</p>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-[#7c93c3]/20 flex items-center justify-center text-xl">
                {style==="japanese"?"⛩️":style==="villa"?"🏡":style==="asian"?"🏯":
                 style==="industrial"?"🏭":style==="scandinavian"?"🏔️":
                 style==="colonial"?"🏛️":style==="classical"?"🏺":"🏢"}
              </div>
              <div>
                <p className="text-sm font-bold capitalize">{style} Building</p>
                <p className="text-[10px] text-white/40">{floors} floors · {glbFilename}</p>
              </div>
              <CheckCircle className="w-4 h-4 text-emerald-400 ml-auto" />
            </div>
          </div>
        ) : (
          <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 p-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
            <p className="text-[10px] text-amber-300">Generate a building first, then export to Unreal Engine.</p>
          </div>
        )}

        {/* UE5 Feature pills */}
        <div className="grid grid-cols-2 gap-2">
          {FEATURES.map(f => (
            <div key={f.label} className="rounded-xl bg-white/5 border border-white/8 p-2.5 flex items-start gap-2">
              <div className="mt-0.5">{f.icon}</div>
              <div>
                <p className="text-[10px] font-bold text-white">{f.label}</p>
                <p className="text-[8px] text-white/40 leading-snug">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* MAIN DOWNLOAD */}
        <button onClick={handleDownload} disabled={!hasBuilding || downloading}
          className={`w-full flex items-center justify-center gap-3 py-3.5 rounded-xl font-bold text-sm transition-all ${
            !hasBuilding
              ? "bg-white/5 text-white/20 cursor-not-allowed"
              : downloaded
              ? "bg-emerald-600 text-white"
              : "bg-[#7c93c3] hover:bg-[#8da3d3] text-white shadow-lg shadow-[#7c93c3]/20"
          }`}>
          {downloading ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Packaging…</>
          ) : downloaded ? (
            <><CheckCircle className="w-4 h-4" /> Downloaded! Run ue5_setup.py</>
          ) : (
            <><Download className="w-4 h-4" /> Download UE5 Package (.zip)</>
          )}
        </button>

        {downloaded && (
          <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/20 p-3 text-[10px] text-emerald-300 space-y-1">
            <p className="font-bold">✓ Package downloaded — next steps:</p>
            <p>1. Unzip the package anywhere on your computer</p>
            <p>2. Open Unreal Engine 5.3+ with your project</p>
            <p>3. Tools → Execute Python Script → select <span className="font-mono bg-white/10 px-1 rounded">ue5_setup.py</span></p>
            <p>4. Wait ~30 seconds → your building appears with full Lumen lighting</p>
          </div>
        )}

        {/* Step-by-step guide */}
        <div className="rounded-xl bg-white/5 border border-white/10 overflow-hidden">
          <p className="text-[9px] font-bold uppercase tracking-wider text-white/40 px-3 pt-3 pb-2">
            Setup Guide
          </p>
          {STEPS.map((step, i) => (
            <div key={i} className="flex items-start gap-3 px-3 py-2.5 border-t border-white/5">
              <div className="w-6 h-6 rounded-full bg-[#7c93c3]/20 flex items-center justify-center text-xs font-bold text-[#7c93c3] flex-shrink-0 mt-0.5">
                {i+1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-base leading-none">{step.icon}</span>
                  <p className="text-[10px] font-bold text-white">{step.label}</p>
                </div>
                <p className="text-[9px] text-white/40 mt-0.5">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* UE5 Console Commands */}
        <div className="rounded-xl bg-black/40 border border-white/10 overflow-hidden">
          <button onClick={() => { setShowCmds(!showCmds); loadChecklist(); }}
            className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-white/5 transition">
            <p className="text-[10px] font-bold text-white/70 flex items-center gap-2">
              <span>{">"}_</span> UE5 Console Commands
            </p>
            {showCmds ? <ChevronUp className="w-3 h-3 text-white/30" /> : <ChevronDown className="w-3 h-3 text-white/30" />}
          </button>
          {showCmds && (
            <div className="px-3 pb-3 space-y-1.5 border-t border-white/10">
              <p className="text-[8px] text-white/30 pt-2">Paste into: Window → Output Log → Cmd</p>
              {CONSOLE_CMDS.map(({label,cmd}) => (
                <div key={cmd} className="flex items-center gap-2">
                  <div className="flex-1 bg-black/60 rounded-lg px-2.5 py-1.5 font-mono text-[9px] text-emerald-400 truncate">
                    {cmd}
                  </div>
                  <button onClick={() => copyCmd(cmd)}
                    className="text-[8px] text-white/30 hover:text-white/60 px-2 py-1.5 rounded-lg hover:bg-white/5 transition flex-shrink-0">
                    {copiedCmd===cmd ? "✓" : "copy"}
                  </button>
                </div>
              ))}

              {/* Photorealism tips from checklist */}
              {loadingCL && <div className="flex justify-center pt-2"><Loader2 className="w-3 h-3 animate-spin text-white/30" /></div>}
              {checklist && (
                <div className="pt-2 border-t border-white/5">
                  <p className="text-[8px] font-bold text-white/40 uppercase mb-1.5">Photorealism Tips</p>
                  {checklist.photorealism_tips.map((tip: string, i: number) => (
                    <p key={i} className="text-[8px] text-white/30 flex gap-1.5">
                      <span className="text-[#7c93c3]">→</span>{tip}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Pipeline diagram */}
        <div className="rounded-xl bg-white/5 border border-white/10 p-3">
          <p className="text-[9px] font-bold uppercase tracking-wider text-white/40 mb-3">Pipeline</p>
          <div className="flex flex-col gap-1">
            {[
              ["🤖","AI Architect","Prompt → LLM → Building Schema"],
              ["⚡","Blender",      "Procedural geometry + PBR materials"],
              ["📦","GLB Export",   "Interchange-compatible, scale 1:1"],
              ["🎮","Unreal 5",     "Nanite + Lumen + Path Tracing"],
              ["🎬","Render",       "4K stills or cinematic video"],
            ].map(([icon,title,desc],i,arr) => (
              <React.Fragment key={title}>
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-[#7c93c3]/10 flex items-center justify-center text-sm flex-shrink-0">
                    {icon}
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-white">{title}</p>
                    <p className="text-[8px] text-white/30">{desc}</p>
                  </div>
                </div>
                {i < arr.length-1 && (
                  <div className="w-0.5 h-3 bg-[#7c93c3]/20 ml-3.5" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Version note */}
        <p className="text-[8px] text-white/20 text-center pb-2">
          Requires Unreal Engine 5.3+ · Tested on UE 5.4.4
        </p>
      </div>
    </div>
  );
}
