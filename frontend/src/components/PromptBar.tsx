"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2, Sparkles, RefreshCw } from "lucide-react";
import { useStore } from "@/lib/store";
import axios from "axios";

const API = "https://ai-architect-production-1e57.up.railway.app";

const SUGGESTIONS = [
  "Modern 3-floor villa with pool and garage",
  "5-storey apartment with red brick walls",
  "Traditional bungalow with garden and flat roof",
  "Contemporary glass house with 4 floors",
];

export default function PromptBar({ buildConfig }: { buildConfig?: any }) {
  const [value, setValue] = useState("");
  const [suggIdx, setSuggIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const { projectId, clientId, isGenerating, plotLat, plotLng, plotWidth, plotDepth } = useStore();
  const setIsGenerating = useStore((s) => s.setIsGenerating);
  const clearAgentLogs = useStore((s) => s.clearAgentLogs);
  const addAgentLog = useStore((s) => s.addAgentLog);
  const updateScene = useStore((s) => s.updateScene);
  const addChatMessage = useStore((s) => s.addChatMessage);
  const updateChatMessage = useStore((s) => s.updateChatMessage);

  // Cycle suggestion placeholder
  useEffect(() => {
    const t = setInterval(() => setSuggIdx((i) => (i + 1) % SUGGESTIONS.length), 3500);
    return () => clearInterval(t);
  }, []);

  // Listen for build-config events from ConfigPanel "Build Now" button
  useEffect(() => {
    const handler = (e: any) => {
      setValue(e.detail);
      inputRef.current?.focus();
    };
    window.addEventListener("build-config", handler);
    return () => window.removeEventListener("build-config", handler);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const prompt = value.trim();
    if (!prompt || isGenerating) return;

    setValue("");
    setIsGenerating(true);
    clearAgentLogs();

    // Add user bubble
    addChatMessage({ role: "user", content: prompt });
    // Add streaming AI bubble
    const aiId = addChatMessage({ role: "assistant", content: "Analysing your request…", isStreaming: true });

    const steps = [
      { delay: 300,  text: "Planning layout and rooms…" },
      { delay: 800,  text: "Generating 3D geometry…" },
      { delay: 1400, text: "Applying materials and finishes…" },
      { delay: 1900, text: "Running NBC compliance audit…" },
    ];

    // Animate agent progress in the AI bubble
    for (const step of steps) {
      setTimeout(() => {
        updateChatMessage(aiId, { content: step.text });
        addAgentLog({ agent: "orchestrator", message: step.text });
      }, step.delay);
    }

    try {
      const response = await axios.post(`${API}/api/agents/generate_simple`, {
        prompt,
        project_id: projectId,
        client_id: clientId,
        plot_lat: plotLat,
        plot_lng: plotLng,
        plot_width: plotWidth,
        plot_depth: plotDepth,
        wall_color: buildConfig?.wallColor || "white",
        roof_style: buildConfig?.roofStyle || "gable",
        window_glass: buildConfig?.windowGlass || "clear",
        floors: buildConfig?.floors ?? 2,
        has_balcony: buildConfig?.balcony ?? true,
        has_garage: buildConfig?.garage ?? true,
        has_pool: buildConfig?.pool ?? false,
        has_garden: buildConfig?.garden ?? true,
      });

      const geo = response.data?.scene_data?.geometry;
      const compliance = response.data?.scene_data?.compliance || null;
      const msg = response.data?.message || "";

      if (geo) {
        const materials = (geo.materials || []).map((m: any) => ({ ...m, id: m.id || m.material_id }));
        updateScene(
          { meshes: geo.meshes || [] },
          { drone_path: [
            { index: 0, position: [18, 8, 18], look_at: [0, 2, 0], duration_s: 4 },
            { index: 1, position: [-18, 8, -18], look_at: [0, 2, 0], duration_s: 4 },
          ]},
          { materials },
          compliance
        );

        // Build a natural-language summary
        const p = prompt.toLowerCase();
        const features: string[] = [];
        if (p.includes("pool") || buildConfig?.pool) features.push("swimming pool");
        if (p.includes("garage") || buildConfig?.garage) features.push("garage");
        if (p.includes("garden") || buildConfig?.garden) features.push("garden");
        if (p.includes("balcon") || buildConfig?.balcony) features.push("balcony");

        const floorsMatch = p.match(/(\d+)[- ]?(floor|stor)/);
        const floors = floorsMatch ? parseInt(floorsMatch[1]) : (buildConfig?.floors ?? 2);
        const btype = p.includes("villa") ? "villa" : p.includes("apartment") ? "apartment" : p.includes("bungalow") ? "bungalow" : "house";

        const summary = [
          `✓ Built! Your **${floors}-floor ${btype}** is ready.`,
          features.length ? `Features: ${features.join(", ")}.` : "",
          compliance
            ? compliance.compliant
              ? `🟢 NBC Compliant — FAR ${compliance.actual_far}/${compliance.allowed_far}, Coverage ${compliance.actual_coverage_pct}%/${compliance.allowed_coverage_pct}%.`
              : `🔴 NBC Issues: ${compliance.issues.slice(0, 2).join(" ")}`
            : "",
          "\nTry: *\"Make it taller\"*, *\"Add a pool\"*, or *\"Change walls to red brick\"*."
        ].filter(Boolean).join(" ");

        updateChatMessage(aiId, {
          content: summary,
          isStreaming: false,
          buildingSummary: {
            type: btype, floors,
            features,
            compliant: compliance?.compliant ?? true,
            far: compliance?.actual_far,
            coverage: compliance?.actual_coverage_pct,
          },
        });
        addAgentLog({ agent: "orchestrator", message: msg || "Generation complete" });
      } else {
        updateChatMessage(aiId, { content: "⚠️ Backend returned no geometry. Try rephrasing your prompt.", isStreaming: false });
      }
    } catch (err) {
      // Fallback mock so UI always shows something
      const fallbackMeshes = [
        { id: "foundation", component_group: "Foundation", type: "box", position: [0,-0.15,0] as [number,number,number], scale: [11,0.3,15] as [number,number,number], material_id: "concrete" },
        { id: "walls", component_group: "Walls", type: "box", position: [0,2.5,0] as [number,number,number], scale: [10,5,14] as [number,number,number], material_id: "plaster_white" },
        { id: "roof", component_group: "Roof", type: "box", position: [0,5.2,0] as [number,number,number], scale: [11,0.25,15] as [number,number,number], material_id: "concrete_dark" },
        { id: "window_f", component_group: "Windows", type: "box", position: [0,2.8,7.1] as [number,number,number], scale: [3,1.4,0.1] as [number,number,number], material_id: "glass_clear" },
        { id: "window_b", component_group: "Windows", type: "box", position: [0,2.8,-7.1] as [number,number,number], scale: [3,1.4,0.1] as [number,number,number], material_id: "glass_clear" },
      ];
      updateScene(
        { meshes: fallbackMeshes },
        { drone_path: [{ index:0, position:[18,8,18], look_at:[0,2,0], duration_s:4 }] },
        { materials: [
          { id:"plaster_white", color_hex:"#f5f5f0", roughness:0.85 },
          { id:"concrete", color_hex:"#b0b8c4", roughness:0.9 },
          { id:"concrete_dark", color_hex:"#8c9ab0", roughness:0.85 },
          { id:"glass_clear", color_hex:"#d0e8f0", roughness:0.05, transmission:0.9, opacity:0.35, transparent:true },
        ]},
        { compliant:false, issues:["Backend unavailable — showing demo model"], actual_far:1.2, allowed_far:2.5, actual_coverage_pct:38, allowed_coverage_pct:60, vastu_suggestions:["Main entrance recommended facing North or East."] }
      );
      updateChatMessage(aiId, {
        content: "⚠️ Couldn't reach the server — showing a demo model. Check your connection and try again.",
        isStreaming: false,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative flex items-center w-full rounded-2xl bg-white border border-slate-200/80 shadow-lg overflow-hidden">
        <Sparkles className="absolute left-4 w-4 h-4 text-[#7c93c3] pointer-events-none" />
        <input
          id="prompt-input"
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={isGenerating}
          placeholder={SUGGESTIONS[suggIdx]}
          className="flex-1 bg-transparent text-sm text-slate-800 placeholder-slate-300 outline-none pl-11 pr-4 py-3.5"
        />
        <div className="flex items-center gap-1 pr-2">
          {value && (
            <button type="button" onClick={() => setValue("")}
              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg">
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            type="submit"
            disabled={isGenerating || !value.trim()}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#7c93c3] hover:bg-[#8da3d3] disabled:opacity-40 disabled:hover:bg-[#7c93c3] text-white font-medium text-xs transition-all duration-200 shadow-sm"
          >
            {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
            {isGenerating ? "Building…" : "Generate"}
          </button>
        </div>
      </div>
    </form>
  );
}
