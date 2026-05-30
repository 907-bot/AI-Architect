"use client";
import StylePicker from "@/components/StylePicker";

import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2, Sparkles, RefreshCw } from "lucide-react";
import { useStore } from "@/lib/store";
import axios from "axios";
import { API_BASE, fallbackVillaGeometry, normalizeMvpResponse } from "@/lib/mvpScene";

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

  const isGenerating = useStore((s) => s.isGenerating);
  const setIsGenerating = useStore((s) => s.setIsGenerating);
  const clearAgentLogs = useStore((s) => s.clearAgentLogs);
  const addAgentLog = useStore((s) => s.addAgentLog);
  const updateScene = useStore((s) => s.updateScene);
  const addChatMessage = useStore((s) => s.addChatMessage);
  const updateChatMessage = useStore((s) => s.updateChatMessage);
  const setGeneratedGlbPath = useStore((s) => s.setGeneratedGlbPath);
  const setLatestToon = useStore((s) => s.setLatestToon);

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
      { delay: 800,  text: "Llama 3.1 is thinking — this takes ~20s…" },
      { delay: 5000, text: "Generating 3D geometry…" },
      { delay: 10000, text: "Applying materials and finishes…" },
      { delay: 15000, text: "Running NBC compliance audit…" },
    ];

    // Animate agent progress in the AI bubble
    for (const step of steps) {
      setTimeout(() => {
        updateChatMessage(aiId, { content: step.text });
        addAgentLog({ agent: "orchestrator", message: step.text });
      }, step.delay);
    }

    try {
      const response = await axios.post(
        `${API_BASE}/api/generate`,
        {
          prompt,
          style: buildConfig?.roofStyle === "gable" ? "craftsman" : "contemporary",
          render_quality: "cinematic",
        },
        { timeout: 120000 },
      );
      const result = response.data?.data || response.data;
      const generated = normalizeMvpResponse(result);
      const geo = generated.geometry;
      const compliance = generated.compliance;
      const msg = response.data?.message || "";

      if (geo) {
        setGeneratedGlbPath(generated.glbPath);
        setLatestToon(generated.toon);
        updateScene(generated.geometry, generated.sceneConfig, generated.assets, compliance || undefined);

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
          `Built. Your **${floors}-floor ${btype}** is ready.`,
          result?.glb_path ? `Blender exported ${result.glb_path}; viewer is synchronized to the SceneGraph layout.` : "Blender was not available to the API, so the viewer is showing compiled procedural geometry.",
          result?.planner ? `Planner: ${result.planner}.` : "",
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
        updateChatMessage(aiId, { content: "Backend returned no geometry. Try rephrasing your prompt.", isStreaming: false });
      }
    } catch (err) {
      // Don't use fallback - show empty state
      updateScene(
        { meshes: [], rooms: [], style: "modern" },
        { drone_path: [] },
        { materials: [] },
        {
          compliant: false,
          issues: ["Backend unavailable - check if server is running on port 8000"],
          actual_far: 0,
          allowed_far: 2.5,
          actual_coverage_pct: 0,
          allowed_coverage_pct: 60,
        }
      );
      setGeneratedGlbPath(null);
      setLatestToon(null);
      updateChatMessage(aiId, {
        content: "Could not reach the backend server. Make sure to run:\n\n```bash\ncd AI-Architect\npython -m uvicorn backend.main:app --port 8000\n```\n\nFor local AI (Ollama/Llama 3.1) and Blender, install them locally.",
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
