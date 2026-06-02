"use client";
import React, { useState, useCallback } from "react";
import { useStore } from "@/lib/store";
import { API_BASE } from "@/lib/mvpScene";
import {
  Ruler, CheckCircle, AlertTriangle, Loader2,
  MapPin, Building2, Lightbulb, ArrowRight
} from "lucide-react";

interface FeasibilityResult {
  feasible: boolean; status: string;
  metrics: { plot_sqm:number; footprint_sqm:number; coverage_pct:number; far_actual:number; far_limit:number; cov_limit:number; };
  issues: string[]; suggestions: string[]; text: string;
}
interface SuggestionResult {
  schema: any; text: string; type: string;
}

export default function PlotFeasibility() {
  const { plotWidth, plotDepth, plotLat, plotLng, setPlotData } = useStore();
  const geometryData = useStore(s => s.geometryData);
  const setIsGenerating = useStore(s => s.setIsGenerating);
  const setGeneratedGlbPath = useStore(s => s.setGeneratedGlbPath);

  const [plotSqm, setPlotSqm]   = useState<number>(plotWidth * plotDepth || 300);
  const [plotW,   setPlotW]     = useState<number>(Math.round(plotWidth || 17));
  const [plotD,   setPlotD]     = useState<number>(Math.round(plotDepth || 17));
  const [result,  setResult]    = useState<FeasibilityResult | null>(null);
  const [suggest, setSuggest]   = useState<SuggestionResult | null>(null);
  const [loading, setLoading]   = useState(false);
  const [mode,    setMode]      = useState<"sqm"|"dimensions">("dimensions");

  const schema   = (geometryData as any)?.schema || {};
  const effPlotSqm = mode === "sqm" ? plotSqm : plotW * plotD;

  const checkFeasibility = useCallback(async () => {
    setLoading(true); setResult(null); setSuggest(null);
    try {
      const r = await fetch(`${API_BASE}/api/feasibility`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plot_area_sqm: effPlotSqm,
          plot_width_m:  plotW, plot_depth_m: plotD,
          building_type: schema.building_type || "apartment",
          floors:        schema.floors || 3,
          width:         schema.width  || 20,
          depth:         schema.depth  || 15,
          country_code:  "IN",
        }),
      });
      setResult(await r.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [effPlotSqm, plotW, plotD, schema]);

  const getSuggestion = useCallback(async () => {
    setLoading(true); setSuggest(null);
    try {
      const r = await fetch(`${API_BASE}/api/suggest-building`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plot_area_sqm: effPlotSqm,
          plot_width_m:  plotW, plot_depth_m: plotD,
          building_type: schema.building_type || "apartment",
        }),
      });
      setSuggest(await r.json());
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [effPlotSqm, plotW, plotD, schema]);

  const generateSuggested = useCallback(async () => {
    if (!suggest?.schema) return;
    setIsGenerating(true);
    try {
      const prompt = `${suggest.schema.floors}-floor ${suggest.schema.building_type} ${suggest.schema.style} style`;
      const resp = await fetch(`${API_BASE}/api/generate`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, style: suggest.schema.style, ...suggest.schema }),
      });
      const data = await resp.json();
      if (data.glb_path || data.model_path) setGeneratedGlbPath(data.glb_path || data.model_path);
    } catch (e) { console.error(e); }
    setIsGenerating(false);
  }, [suggest, setIsGenerating, setGeneratedGlbPath]);

  // Sync plot dimensions to map
  const syncToMap = () => {
    setPlotData(plotLat, plotLng, plotW, plotD);
  };

  const maxBuildable = Math.floor(effPlotSqm * 0.50); // 50% coverage
  const estFloors    = Math.min(10, Math.floor((effPlotSqm * 3.5) / Math.min(maxBuildable, effPlotSqm * 0.45)));

  return (
    <div className="p-4 space-y-4">
      <div>
        <h3 className="text-xs font-bold text-slate-700 flex items-center gap-2">
          <Ruler className="w-3.5 h-3.5 text-[#7c93c3]" /> Plot Size & Feasibility
        </h3>
        <p className="text-[9px] text-slate-400 mt-0.5">
          Enter your plot dimensions to check if your building fits
        </p>
      </div>

      {/* Mode toggle */}
      <div className="flex rounded-lg bg-slate-100 p-0.5 gap-0.5">
        {[["dimensions","W × D"], ["sqm","Sq Metres"]].map(([m,l]) => (
          <button key={m} onClick={() => setMode(m as "sqm"|"dimensions")}
            className={`flex-1 py-1.5 rounded text-[9px] font-semibold transition ${
              mode === m ? "bg-white text-slate-800 shadow-sm" : "text-slate-500"
            }`}>{l}</button>
        ))}
      </div>

      {/* Inputs */}
      {mode === "dimensions" ? (
        <div className="grid grid-cols-2 gap-2">
          {[["Width (m)", plotW, setPlotW], ["Depth (m)", plotD, setPlotD]].map(([label, val, setter]) => (
            <div key={String(label)}>
              <label className="text-[9px] font-medium text-slate-500 block mb-1">{String(label)}</label>
              <input type="number" min={4} max={100} step={0.5}
                value={Number(val)}
                onChange={e => { (setter as Function)(parseFloat(e.target.value)||0); }}
                className="w-full border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-[#7c93c3]"
              />
            </div>
          ))}
          <div className="col-span-2">
            <div className="flex items-center justify-between">
              <p className="text-[9px] text-slate-400">Total area</p>
              <p className="text-[10px] font-bold text-slate-700">{(plotW*plotD).toFixed(0)} m²</p>
            </div>
          </div>
        </div>
      ) : (
        <div>
          <label className="text-[9px] font-medium text-slate-500 block mb-1">Plot area (sq metres)</label>
          <input type="number" min={50} max={10000} step={10}
            value={plotSqm}
            onChange={e => setPlotSqm(parseFloat(e.target.value)||0)}
            className="w-full border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-[#7c93c3]"
          />
        </div>
      )}

      {/* Quick stats */}
      <div className="grid grid-cols-3 gap-1.5">
        {[
          ["Max Coverage",  `${maxBuildable}m²`, "50% of plot"],
          ["Max Floors",    `${estFloors}`,       "NBC FAR 3.5"],
          ["Plot Area",     `${effPlotSqm.toFixed(0)}m²`, mode==="dimensions"?`${plotW}×${plotD}m`:""],
        ].map(([k,v,s]) => (
          <div key={String(k)} className="bg-slate-50 rounded-xl p-2 text-center border border-slate-100">
            <p className="text-[8px] text-slate-400">{k}</p>
            <p className="text-[11px] font-bold text-slate-700">{v}</p>
            {s && <p className="text-[7px] text-slate-400">{s}</p>}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button onClick={checkFeasibility} disabled={loading || effPlotSqm < 10}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-[#7c93c3] hover:bg-[#8da3d3] disabled:bg-slate-200 text-white disabled:text-slate-400 rounded-xl text-[10px] font-semibold transition">
          {loading ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle className="w-3 h-3" />}
          Check Feasibility
        </button>
        <button onClick={getSuggestion} disabled={loading || effPlotSqm < 10}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-white border border-[#7c93c3] hover:bg-[#7c93c3]/10 disabled:border-slate-200 text-[#7c93c3] disabled:text-slate-400 rounded-xl text-[10px] font-semibold transition">
          <Lightbulb className="w-3 h-3" /> AI Suggest
        </button>
      </div>

      <button onClick={syncToMap}
        className="w-full text-[9px] text-slate-400 hover:text-[#7c93c3] transition flex items-center justify-center gap-1">
        <MapPin className="w-3 h-3" /> Sync dimensions to map plot
      </button>

      {/* Feasibility Result */}
      {result && (
        <div className={`rounded-xl border p-3 space-y-2 ${
          result.feasible ? "bg-emerald-50 border-emerald-200" : "bg-amber-50 border-amber-200"
        }`}>
          <div className="flex items-center gap-2">
            {result.feasible
              ? <CheckCircle className="w-4 h-4 text-emerald-500" />
              : <AlertTriangle className="w-4 h-4 text-amber-500" />}
            <span className={`text-[10px] font-bold ${result.feasible?"text-emerald-700":"text-amber-700"}`}>
              {result.status}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-1">
            {[
              ["Coverage",  `${result.metrics.coverage_pct}%`,  `limit ${result.metrics.cov_limit}%`],
              ["FAR",       `${result.metrics.far_actual}`,      `limit ${result.metrics.far_limit}`],
              ["Footprint", `${result.metrics.footprint_sqm}m²`, `of ${result.metrics.plot_sqm}m²`],
            ].map(([k,v,s]) => (
              <div key={String(k)} className="bg-white/70 rounded-lg p-1.5 text-center">
                <p className="text-[8px] text-slate-400">{k}</p>
                <p className="text-[10px] font-bold text-slate-700">{v}</p>
                <p className="text-[7px] text-slate-400">{s}</p>
              </div>
            ))}
          </div>
          {result.issues.length > 0 && (
            <div className="space-y-0.5">
              {result.issues.map((issue,i) => (
                <p key={i} className="text-[9px] text-amber-700 flex gap-1">
                  <span>•</span>{issue}
                </p>
              ))}
            </div>
          )}
          {result.suggestions.length > 0 && (
            <div className="space-y-1">
              <p className="text-[8px] font-bold text-slate-500 uppercase">Suggestions</p>
              {result.suggestions.map((s,i) => (
                <p key={i} className="text-[9px] text-slate-600 flex gap-1">
                  <ArrowRight className="w-2.5 h-2.5 mt-0.5 flex-shrink-0 text-[#7c93c3]" />{s}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* AI Suggestion */}
      {suggest && (
        <div className="rounded-xl bg-[#7c93c3]/10 border border-[#7c93c3]/20 p-3 space-y-2">
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-[#7c93c3]" />
            <span className="text-[10px] font-bold text-[#5a73a3]">AI Recommended Design</span>
          </div>
          <p className="text-[9px] text-slate-600 whitespace-pre-line leading-relaxed">{suggest.text}</p>
          <button onClick={generateSuggested}
            className="w-full py-2 bg-[#7c93c3] hover:bg-[#8da3d3] text-white text-[10px] font-bold rounded-xl transition flex items-center justify-center gap-2">
            <Building2 className="w-3 h-3" /> Generate This Building
          </button>
        </div>
      )}
    </div>
  );
}
