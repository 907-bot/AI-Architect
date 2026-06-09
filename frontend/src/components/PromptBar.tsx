"use client";
import StylePicker, { STYLES } from "@/components/StylePicker";

import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2, Sparkles, RefreshCw, Pencil, PlusCircle, ChevronDown, ChevronUp } from "lucide-react";
import { useStore } from "@/lib/store";
import axios from "axios";
import { API_BASE, fallbackVillaGeometry, normalizeMvpResponse } from "@/lib/mvpScene";

const SUGGESTIONS = [
  "Modern 3-floor villa with pool and garage",
  "5-storey apartment with red brick walls",
  "Traditional bungalow with garden and flat roof",
  "Contemporary glass house with 4 floors",
];

/** Keywords that signal the user wants to EDIT, not generate fresh */
const EDIT_KEYWORDS = [
  "make it", "add a", "add the", "remove the", "change the", "change it",
  "taller", "wider", "shorter", "smaller", "bigger", "larger",
  "more floors", "fewer floors", "extra floor",
  "flat roof", "gable roof", "hip roof",
  "red brick", "white walls", "glass walls",
  "make the", "increase", "decrease", "reduce",
  // Additional patterns for EDIT_CHIPS and common phrasings
  "add one more", "one more floor", "more floor", "remove a", "remove one",
  "add pool", "swimming pool", "add garage", "wider rooms", "all rooms",
  "make all", "remove floor", "subtract floor", "fewer floor", "less floor",
  "add 1 floor", "add 2 floor", "add 3 floor",
];


function isEditIntent(prompt: string): boolean {
  const lower = prompt.toLowerCase();
  return EDIT_KEYWORDS.some((kw) => lower.includes(kw));
}

/** Quick-prompt chips shown above the input when no building exists */
const STYLE_PROMPTS: { style: string; label: string; emoji: string; prompt: string }[] = [
  { style: "modern",       label: "Modern Villa",      emoji: "🏢", prompt: "Modern 3-floor villa with flat roof, glass walls and rooftop pool" },
  { style: "japanese",     label: "Japanese Home",     emoji: "⛩️", prompt: "Japanese-style 2-floor house with pagoda roof, zen garden and wooden facade" },
  { style: "villa",        label: "Mediterranean",     emoji: "🏡", prompt: "Mediterranean villa with hip roof, terracotta tiles, arched windows and garden" },
  { style: "scandinavian", label: "Scandinavian",      emoji: "🏔️", prompt: "Scandinavian 2-floor house with steep gable roof, light wood and minimalist design" },
  { style: "colonial",     label: "Colonial",          emoji: "🏛️", prompt: "Colonial bungalow with white columns, large gable roof, wraparound porch and garden" },
  { style: "industrial",   label: "Industrial Loft",   emoji: "🏭", prompt: "Industrial loft-style house with exposed red brick, steel beams and large windows" },
  { style: "asian",        label: "Asian Palace",      emoji: "🏯", prompt: "Asian palace-style 3-floor residence with curved roofs, red columns and courtyard" },
  { style: "classical",    label: "Neo-Classical",     emoji: "🏺", prompt: "Neo-classical mansion with marble facade, grand portico, symmetrical columns and dome" },
];

/** Quick-edit chips shown when a building already exists */
const EDIT_CHIPS = [
  { label: "Add pool",          prompt: "Add a swimming pool" },
  { label: "+1 Floor",          prompt: "Add one more floor" },
  { label: "Flat roof",         prompt: "Change roof to flat" },
  { label: "Gable roof",        prompt: "Change roof to gable" },
  { label: "Red brick",         prompt: "Change walls to red brick" },
  { label: "Glass facade",      prompt: "Change exterior to glass facade" },
  { label: "Add garage",        prompt: "Add a garage" },
  { label: "Wider rooms",       prompt: "Make all rooms larger" },
];

export default function PromptBar({ buildConfig }: { buildConfig?: any }) {
  const [value, setValue] = useState("");
  const [suggIdx, setSuggIdx] = useState(0);
  const [showStyleChips, setShowStyleChips] = useState(true);
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
  const latestToon = useStore((s) => s.latestToon);
  const setFloorplanUrl = useStore((s) => s.setFloorplanUrl);
  const setBoqData = useStore((s) => s.setBoqData);
  const calculateBoq = useStore((s) => s.calculateBoq);
  const zoningData = useStore((s) => s.zoningData);

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

  // Listen for edit-prompt events from Edit tab
  useEffect(() => {
    const handler = (e: any) => {
      setValue(e.detail);
      inputRef.current?.focus();
    };
    window.addEventListener("edit-prompt", handler);
    return () => window.removeEventListener("edit-prompt", handler);
  }, []);

  const hasBuilding = !!latestToon;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const prompt = value.trim();
    if (!prompt || isGenerating) return;

    setValue("");
    setIsGenerating(true);
    clearAgentLogs();

    // Determine if this is a fresh generate or an edit
    const useEdit = hasBuilding && isEditIntent(prompt);
    const endpoint = useEdit ? `${API_BASE}/api/edit` : `${API_BASE}/api/generate`;

    // Add user bubble
    addChatMessage({ role: "user", content: prompt });
    const aiId = addChatMessage({
      role: "assistant",
      content: useEdit ? "✏️ Editing your building…" : "Analysing your request…",
      isStreaming: true,
    });

    if (!useEdit) {
      // Animate progress steps only for fresh generation
      const steps = [
        { delay: 300,   text: "Planning layout and rooms…" },
        { delay: 800,   text: "Llama 3.1 is thinking — this takes ~20s…" },
        { delay: 5000,  text: "Generating 3D geometry…" },
        { delay: 10000, text: "Applying materials and finishes…" },
        { delay: 15000, text: "Running NBC compliance audit…" },
      ];
      for (const step of steps) {
        setTimeout(() => {
          updateChatMessage(aiId, { content: step.text });
          addAgentLog({ agent: "orchestrator", message: step.text });
        }, step.delay);
      }
    }

    try {
      let response;
      if (useEdit) {
        response = await axios.post(
          endpoint,
          { toon: latestToon, instruction: prompt },
          { timeout: 60000 },
        );
      } else {
        response = await axios.post(
          endpoint,
          {
            prompt,
            style: buildConfig?.roofStyle === "gable" ? "craftsman" : "contemporary",
            render_quality: "cinematic",
            zoning_data: zoningData,
          },
          { timeout: 120000 },
        );
      }

      const result = response.data?.data || response.data;
      const generated = normalizeMvpResponse(result);
      const geo = generated.geometry;
      const compliance = generated.compliance;
      const msg = response.data?.message || "";

      if (geo) {
        setGeneratedGlbPath(generated.glbPath);
        setLatestToon(generated.toon);
        updateScene(generated.geometry, generated.sceneConfig, generated.assets, compliance || undefined);

        if (result.floorplan_url) setFloorplanUrl(result.floorplan_url);
        if (result.boq_data) {
          setBoqData(result.boq_data);
          // Also populate boqSpec from backend dimensions so BOQPanel works
          const bld = result.boq_data.building || {};
          const area = (bld.width || 20) * (bld.depth || 15);
          if (area > 0) calculateBoq(area, 'standard');
        }

        if (useEdit) {
          const changedList: string[] = result.changed || [];
          updateChatMessage(aiId, {
            content: changedList.length
              ? `✅ Done! Modified: **${changedList.join(", ")}**. The 3D model has been updated.`
              : `✅ Applied: "${prompt}". 3D model updated.`,
            isStreaming: false,
          });
        } else {
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
            result?.glb_path
              ? `Blender exported ${result.glb_path}; viewer is synchronized.`
              : "Viewer showing procedural geometry.",
            result?.planner ? `Planner: ${result.planner}.` : "",
            features.length ? `Features: ${features.join(", ")}.` : "",
            compliance
              ? compliance.compliant
                ? `🟢 NBC Compliant — FAR ${compliance.actual_far}/${compliance.allowed_far}, Coverage ${compliance.actual_coverage_pct}%/${compliance.allowed_coverage_pct}%.`
                : `🔴 NBC Issues: ${compliance.issues.slice(0, 2).join(" ")}`
              : "",
            "\nTry: *\"Make it taller\"*, *\"Add a pool\"*, or *\"Change walls to red brick\"*.",
          ].filter(Boolean).join(" ");

          updateChatMessage(aiId, {
            content: summary,
            isStreaming: false,
            buildingSummary: {
              type: btype, floors, features,
              compliant: compliance?.compliant ?? true,
              far: compliance?.actual_far,
              coverage: compliance?.actual_coverage_pct,
            },
          });
        }
        addAgentLog({ agent: "orchestrator", message: msg || (useEdit ? "Edit complete" : "Generation complete") });
      } else {
        updateChatMessage(aiId, {
          content: "Backend returned no geometry. Try rephrasing your prompt.",
          isStreaming: false,
        });
      }
    } catch (err) {
      updateScene(
        { meshes: [], rooms: [], style: "modern" },
        { drone_path: [] },
        { materials: [] },
        {
          compliant: false,
          issues: ["Backend unavailable - check if server is running on port 8000"],
          actual_far: 0, allowed_far: 2.5,
          actual_coverage_pct: 0, allowed_coverage_pct: 60,
        }
      );
      setGeneratedGlbPath(null);
      setLatestToon(null);
      updateChatMessage(aiId, {
        content: "Could not reach the backend server. Make sure to run:\n\n```bash\ncd AI-Architect\npython -m uvicorn backend.main:app --port 8000\n```",
        isStreaming: false,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="w-full flex flex-col gap-2">

      {/* ── Quick chips row ── */}
      {!hasBuilding ? (
        /* Style chips — shown when no building generated yet */
        <div className="flex flex-col gap-1.5">
          <button
            type="button"
            onClick={() => setShowStyleChips((v) => !v)}
            className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest text-slate-400 hover:text-slate-600 transition px-1"
          >
            <PlusCircle className="w-3 h-3" />
            Quick start — pick a style
            {showStyleChips ? <ChevronUp className="w-3 h-3 ml-auto" /> : <ChevronDown className="w-3 h-3 ml-auto" />}
          </button>
          {showStyleChips && (
            <div className="grid grid-cols-4 gap-1">
              {STYLE_PROMPTS.map((s) => (
                <button
                  key={s.style}
                  type="button"
                  disabled={isGenerating}
                  onClick={() => {
                    setValue(s.prompt);
                    inputRef.current?.focus();
                  }}
                  className="flex flex-col items-center gap-0.5 rounded-xl border border-slate-100 bg-white hover:border-[#7c93c3]/50 hover:bg-[#7c93c3]/5 px-1.5 py-1.5 transition-all disabled:opacity-40 group"
                >
                  <span className="text-base leading-none">{s.emoji}</span>
                  <span className="text-[8px] font-semibold text-slate-600 group-hover:text-[#5a73a3] text-center leading-tight">
                    {s.label}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Edit chips — shown when a building already exists */
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest text-[#7c93c3] px-1">
            <Pencil className="w-3 h-3" />
            Edit your building
          </div>
          <div className="flex flex-wrap gap-1">
            {EDIT_CHIPS.map((chip) => (
              <button
                key={chip.label}
                type="button"
                disabled={isGenerating}
                onClick={() => {
                  setValue(chip.prompt);
                  inputRef.current?.focus();
                }}
                className="text-[9px] font-semibold px-2.5 py-1 rounded-lg border border-[#7c93c3]/30 bg-[#7c93c3]/5 hover:bg-[#7c93c3]/15 hover:border-[#7c93c3]/60 text-[#5a73a3] transition-all disabled:opacity-40"
              >
                {chip.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Main input bar ── */}
      <form onSubmit={handleSubmit} className="w-full">
        <div className="relative flex items-center w-full rounded-2xl bg-white border border-slate-200/80 shadow-lg overflow-hidden">
          {hasBuilding ? (
            <Pencil className="absolute left-4 w-4 h-4 text-[#7c93c3] pointer-events-none" />
          ) : (
            <Sparkles className="absolute left-4 w-4 h-4 text-[#7c93c3] pointer-events-none" />
          )}
          <input
            id="prompt-input"
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            disabled={isGenerating}
            placeholder={
              hasBuilding
                ? "e.g. Add a pool, make it taller, flat roof…"
                : SUGGESTIONS[suggIdx]
            }
            className="flex-1 bg-transparent text-sm text-slate-800 placeholder-slate-300 outline-none pl-11 pr-4 py-3.5"
          />
          <div className="flex items-center gap-1 pr-2">
            {value && (
              <button
                type="button"
                onClick={() => setValue("")}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            )}
            <button
              type="submit"
              disabled={isGenerating || !value.trim()}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#7c93c3] hover:bg-[#8da3d3] disabled:opacity-40 disabled:hover:bg-[#7c93c3] text-white font-medium text-xs transition-all duration-200 shadow-sm"
            >
              {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : (hasBuilding ? <Pencil className="w-3.5 h-3.5" /> : <Send className="w-3.5 h-3.5" />)}
              {isGenerating ? (hasBuilding ? "Editing…" : "Building…") : (hasBuilding ? "Edit" : "Generate")}
            </button>
          </div>
        </div>

        {/* Mode indicator */}
        {hasBuilding && !isGenerating && (
          <p className="text-[8px] text-slate-400 text-center mt-1">
            ✏️ Edit mode — your building is loaded. Type a change or{" "}
            <button
              type="button"
              onClick={() => setLatestToon(null)}
              className="underline text-[#7c93c3] hover:text-[#5a73a3]"
            >
              start fresh
            </button>
          </p>
        )}
      </form>
    </div>
  );
}
