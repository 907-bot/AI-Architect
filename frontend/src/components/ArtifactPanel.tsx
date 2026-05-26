"use client";

import React, { useState, useEffect } from "react";
import {
  Image, Video, Layout, Box, HardHat,
  Tool, Vr, Download, Clock, CheckCircle2,
  AlertTriangle, Loader2, ChevronRight
} from "lucide-react";
import { useStore, OutputMode, ArtifactInfo } from "@/lib/store";

const OUTPUT_MODES: { id: OutputMode; label: string; icon: React.ReactNode; description: string; time: string }[] = [
  { id: "fast_preview", label: "Fast Preview", icon: <Box className="w-3.5 h-3.5" />, description: "Quick 3D preview", time: "~5s" },
  { id: "architectural_concept", label: "Arch Concept", icon: <Image className="w-3.5 h-3.5" />, description: "Stylized renders", time: "~25s" },
  { id: "realistic_visualization", label: "Realistic", icon: <Image className="w-3.5 h-3.5" />, description: "Photorealistic", time: "~85s" },
  { id: "technical_floorplan", label: "Floorplan", icon: <Layout className="w-3.5 h-3.5" />, description: "2D floor plans", time: "~2s" },
  { id: "construction_bim", label: "BIM Export", icon: <HardHat className="w-3.5 h-3.5" />, description: "BIM/IFC export", time: "~30s" },
  { id: "xr_export", label: "XR Export", icon: <Vr className="w-3.5 h-3.5" />, description: "Unreal/Unity", time: "~15s" },
  { id: "fabrication_cad", label: "CAD Export", icon: <Tool className="w-3.5 h-3.5" />, description: "CAD/STL/OBJ", time: "~20s" },
  { id: "marketing_walkthrough", label: "Walkthrough", icon: <Video className="w-3.5 h-3.5" />, description: "Cinematic video", time: "~205s" },
];

const STAGE_LABELS: Record<string, string> = {
  floorplan: "Floor Plan",
  preview: "3D Preview",
  furnished: "Furnished",
  cinematic: "Cinematic Render",
  walkthrough: "Walkthrough Video",
  bim_export: "BIM Export",
  gltf_export: "glTF Export",
  cad_export: "CAD Export",
};

const STAGE_ICONS: Record<string, React.ReactNode> = {
  floorplan: <Layout className="w-3 h-3" />,
  preview: <Box className="w-3 h-3" />,
  furnished: <Box className="w-3 h-3" />,
  cinematic: <Image className="w-3 h-3" />,
  walkthrough: <Video className="w-3 h-3" />,
};

export default function ArtifactPanel() {
  const {
    activeOutputMode, setActiveOutputMode,
    artifacts, artifactGenerationStatus, setArtifactGenerationStatus,
    addArtifact, designStyle, setDesignStyle, designStyles, setDesignStyles,
    geometryData,
  } = useStore();

  const [isGenerating, setIsGenerating] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    fetch(`${API_BASE}/api/styles`)
      .then(r => r.json())
      .then(data => {
        if (data.styles) setDesignStyles(data.styles);
      })
      .catch(() => {});
  }, []);

  const handleGenerate = async () => {
    if (!geometryData || isGenerating) return;

    setIsGenerating(true);
    setArtifactGenerationStatus("generating");

    try {
      const resp = await fetch(`${API_BASE}/api/artifacts/generate-progressive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scene_id: "current-scene",
          scene_graph: geometryData,
          output_mode: activeOutputMode,
        }),
      });

      const data = await resp.json();
      if (data.artifacts) {
        data.artifacts.forEach((a: ArtifactInfo) => addArtifact(a));
      }
      setArtifactGenerationStatus(
        data.status === "completed" || data.status === "partial" ? "completed" : "failed"
      );
    } catch {
      setArtifactGenerationStatus("failed");
    } finally {
      setIsGenerating(false);
    }
  };

  const currentMode = OUTPUT_MODES.find(m => m.id === activeOutputMode) || OUTPUT_MODES[0];

  return (
    <div className="glass-panel rounded-xl overflow-hidden">
      <div className="p-3 border-b border-slate-100">
        <div className="flex items-center gap-2 text-slate-700 mb-2">
          <Image className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-[10px] font-semibold uppercase tracking-wider font-outfit">Artifact Pipeline</span>
        </div>

        {/* Output Mode Selector */}
        <div className="space-y-1 max-h-32 overflow-y-auto">
          {OUTPUT_MODES.map((mode) => (
            <button
              key={mode.id}
              onClick={() => setActiveOutputMode(mode.id)}
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-[10px] text-left border transition ${
                activeOutputMode === mode.id
                  ? "bg-[#7c93c3]/20 border-[#7c93c3] text-slate-800"
                  : "bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100"
              }`}
            >
              {mode.icon}
              <div className="flex-1 min-w-0">
                <div className="font-medium">{mode.label}</div>
                <div className="text-[8px] text-slate-400">{mode.description}</div>
              </div>
              <span className="text-[8px] text-slate-400 font-mono">{mode.time}</span>
            </button>
          ))}
        </div>

        {/* Design Style Selector */}
        {designStyles.length > 0 && (
          <div className="mt-2">
            <div className="text-[9px] text-slate-400 font-medium mb-1">Design Style</div>
            <select
              value={designStyle}
              onChange={(e) => setDesignStyle(e.target.value)}
              className="w-full text-[10px] bg-slate-50 border border-slate-200 rounded px-2 py-1 text-slate-700"
            >
              {(designStyles || []).map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Generate Button */}
      <div className="p-3 border-b border-slate-100">
        <button
          onClick={handleGenerate}
          disabled={isGenerating || !geometryData}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-lg text-[11px] font-bold
            bg-[#7c93c3] text-white hover:bg-[#6a7fb0] disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          {isGenerating ? (
            <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generating...</>
          ) : artifactGenerationStatus === "completed" ? (
            <><CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" /> Regenerate</>
          ) : (
            <><Download className="w-3.5 h-3.5" /> Generate Artifacts</>
          )}
        </button>
      </div>

      {/* Artifact Status List */}
      {artifacts.length > 0 && (
        <div className="p-3 space-y-1.5">
          <div className="text-[9px] text-slate-400 font-semibold uppercase tracking-wider">Generated Artifacts</div>
          {(artifacts || []).map((artifact, idx) => (
            <div key={idx} className="flex items-center gap-2 text-[10px] p-1.5 rounded bg-slate-50 border border-slate-100">
              <div className="flex-shrink-0">
                {artifact.status === "completed" ? (
                  <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                ) : artifact.status === "failed" ? (
                  <AlertTriangle className="w-3 h-3 text-rose-500" />
                ) : artifact.status === "processing" ? (
                  <Loader2 className="w-3 h-3 text-amber-500 animate-spin" />
                ) : (
                  <Clock className="w-3 h-3 text-slate-400" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-slate-700">{STAGE_LABELS[artifact.stage] || artifact.stage}</div>
                <div className="text-[8px] text-slate-400">{artifact.artifact_type.toUpperCase()}</div>
              </div>
              {artifact.url && artifact.status === "completed" && (
                <a
                  href={artifact.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-0.5 text-[#7c93c3] hover:underline"
                >
                  <ChevronRight className="w-3 h-3" />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
