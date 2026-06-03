"use client";
import React, { useState, useCallback } from "react";
import { useStore } from "@/lib/store";
import { API_BASE } from "@/lib/mvpScene";
import {
  Settings, RefreshCw, Loader2, ChevronDown,
  Palette, Layers, Home, Droplets, Car,
  LayoutGrid, X, Check
} from "lucide-react";

const ROOF_OPTIONS = [
  {id:"flat",        label:"Flat",         emoji:"▬"},
  {id:"gable",       label:"Gable",        emoji:"🏠"},
  {id:"hip",         label:"Hip",          emoji:"⌂"},
  {id:"pagoda",      label:"Pagoda",       emoji:"⛩️"},
  {id:"curved",      label:"Curved",       emoji:"🌙"},
  {id:"shed",        label:"Shed/Mono",    emoji:"📐"},
  {id:"steep_gable", label:"Steep Gable",  emoji:"🏔️"},
  {id:"pitched",     label:"Pitched",      emoji:"🏛️"},
];

const STYLE_OPTIONS = [
  {id:"modern",       label:"Modern",       emoji:"🏢"},
  {id:"japanese",     label:"Japanese",     emoji:"⛩️"},
  {id:"villa",        label:"Villa",        emoji:"🏡"},
  {id:"asian",        label:"Asian",        emoji:"🏯"},
  {id:"scandinavian", label:"Scandinavian", emoji:"🏔️"},
  {id:"industrial",   label:"Industrial",   emoji:"🏭"},
  {id:"colonial",     label:"Colonial",     emoji:"🏛️"},
  {id:"classical",    label:"Classical",    emoji:"🏺"},
  {id:"mughal",       label:"Mughal",       emoji:"🕌"},
  {id:"craftsman",    label:"Craftsman",    emoji:"🪵"},
  {id:"victorian",    label:"Victorian",    emoji:"🎠"},
  {id:"moroccan",     label:"Moroccan",     emoji:"🧱"},
];

const FLOOR_MATERIALS = [
  {id:"wood",       label:"Wood",       color:"#8b6914"},
  {id:"dark_wood",  label:"Dark Wood",  color:"#4a2c0a"},
  {id:"marble",     label:"Marble",     color:"#e8e4dc"},
  {id:"tile",       label:"Tile",       color:"#b0c4d0"},
  {id:"concrete",   label:"Concrete",   color:"#9a9a96"},
  {id:"carpet",     label:"Carpet",     color:"#8a7060"},
  {id:"tatami",     label:"Tatami",     color:"#c8b870"},
  {id:"terracotta", label:"Terracotta", color:"#b85c38"},
];

const WALL_COLORS = [
  {id:"white",      label:"White",      hex:"#f2f1ef"},
  {id:"cream",      label:"Cream",      hex:"#f2e4cc"},
  {id:"grey",       label:"Grey",       hex:"#b8b8bc"},
  {id:"sage",       label:"Sage",       hex:"#9eb694"},
  {id:"navy",       label:"Navy",       hex:"#2d384f"},
  {id:"terracotta", label:"Terracotta", hex:"#b86138"},
  {id:"charcoal",   label:"Charcoal",   hex:"#383838"},
  {id:"blush",      label:"Blush",      hex:"#ebc8ba"},
];

const FURNITURE_STYLES = [
  {id:"modern",      label:"Modern"},
  {id:"scandinavian",label:"Scandinavian"},
  {id:"luxury",      label:"Luxury"},
  {id:"japanese",    label:"Japanese"},
  {id:"industrial",  label:"Industrial"},
  {id:"classic",     label:"Classic"},
  {id:"minimal",     label:"Minimal"},
  {id:"bohemian",    label:"Bohemian"},
];

interface EditState {
  style:          string;
  roof_style:     string;
  floors:         number;
  balconies:      boolean;
  pool:           boolean;
  garage:         boolean;
  floor_material: string;
  wall_color:     string;
  furniture_style:string;
}

export default function ElementEditor({ onClose }: { onClose?: () => void }) {
  const geometryData        = useStore(s => s.geometryData);
  const generatedGlbPath    = useStore(s => s.generatedGlbPath);
  const setIsGenerating     = useStore(s => s.setIsGenerating);
  const setGeneratedGlbPath = useStore(s => s.setGeneratedGlbPath);
  const addChatMessage      = useStore(s => s.addChatMessage);
  const updateChatMessage   = useStore(s => s.updateChatMessage);

  const schema = (geometryData as any)?.schema || {};

  const [edit, setEdit] = useState<EditState>({
    style:           schema.style           || "modern",
    roof_style:      schema.roof_style      || "flat",
    floors:          schema.floors          || 3,
    balconies:       schema.balconies       ?? true,
    pool:            !!schema.pool,
    garage:          !!schema.garage,
    floor_material:  schema.interior?.floor_material || "wood",
    wall_color:      schema.interior?.wall_color     || "white",
    furniture_style: schema.interior?.furniture_style|| "modern",
  });

  const [regen, setRegen]       = useState(false);
  const [section, setSection]   = useState<string>("exterior");
  const [changed, setChanged]   = useState(false);

  const update = (key: keyof EditState, val: any) => {
    setEdit(prev => ({ ...prev, [key]: val }));
    setChanged(true);
  };

  const regenerate = useCallback(async () => {
    setRegen(true);
    const newSchema = {
      ...schema,
      style:      edit.style,
      roof_style: edit.roof_style,
      floors:     edit.floors,
      balconies:  edit.balconies,
      pool:       edit.pool ? (schema.pool || { enabled:true, width:12, length:6, depth:1.8 }) : null,
      garage:     edit.garage ? (schema.garage || { enabled:true, capacity:2 }) : null,
      interior: {
        ...(schema.interior || {}),
        floor_material:  edit.floor_material,
        wall_color:      edit.wall_color,
        furniture_style: edit.furniture_style,
      },
    };

    const msgId = addChatMessage({
      role: "assistant",
      content: `Regenerating with ${edit.style} style, ${edit.floors}-floor, ${edit.roof_style} roof…`,
      isStreaming: true,
    });

    try {
      const resp = await fetch(`${API_BASE}/api/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: `${edit.floors}-floor ${schema.building_type||"apartment"} ${edit.style} style with ${edit.roof_style} roof`,
          style: edit.style,
          ...newSchema,
        }),
      });
      const data = await resp.json();
      if (data.glb_path || data.model_path) {
        setGeneratedGlbPath(data.glb_path || data.model_path);
      }
      updateChatMessage(msgId, {
        isStreaming: false,
        content: data.message || `✅ Building updated — ${edit.style} style, ${edit.floors} floors, ${edit.roof_style} roof.`,
      });
      setChanged(false);
    } catch (e) {
      updateChatMessage(msgId, { isStreaming: false, content: "❌ Regeneration failed. Try again." });
    }
    setRegen(false);
    setIsGenerating(false);
  }, [edit, schema, addChatMessage, updateChatMessage, setGeneratedGlbPath, setIsGenerating]);

  if (!generatedGlbPath) return null;

  const SECTIONS = [
    { id:"exterior", icon:<Home className="w-3 h-3"/>,     label:"Exterior" },
    { id:"interior", icon:<LayoutGrid className="w-3 h-3"/>,label:"Interior" },
    { id:"features", icon:<Droplets className="w-3 h-3"/>, label:"Features" },
  ];

  return (
    <div className="flex flex-col h-full bg-white border-l border-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-slate-100 bg-white sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <Settings className="w-3.5 h-3.5 text-[#7c93c3]" />
          <span className="text-xs font-bold text-slate-700">Edit Building</span>
        </div>
        <div className="flex items-center gap-1.5">
          {changed && (
            <button onClick={regenerate} disabled={regen}
              className="flex items-center gap-1 px-2.5 py-1.5 bg-[#7c93c3] hover:bg-[#8da3d3] text-white text-[9px] font-bold rounded-lg transition">
              {regen ? <Loader2 className="w-3 h-3 animate-spin"/> : <RefreshCw className="w-3 h-3"/>}
              Regenerate
            </button>
          )}
          {onClose && (
            <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded transition">
              <X className="w-3.5 h-3.5 text-slate-400"/>
            </button>
          )}
        </div>
      </div>

      {/* Section tabs */}
      <div className="flex border-b border-slate-100 bg-slate-50">
        {SECTIONS.map(s => (
          <button key={s.id} onClick={() => setSection(s.id)}
            className={`flex-1 flex items-center justify-center gap-1 py-2 text-[9px] font-semibold transition border-b-2 ${
              section===s.id
                ? "border-[#7c93c3] text-[#7c93c3] bg-white"
                : "border-transparent text-slate-400 hover:text-slate-600"
            }`}>
            {s.icon}{s.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">

        {/* ── EXTERIOR ─────────────────────────────────────────── */}
        {section === "exterior" && (<>

          {/* Style */}
          <div>
            <label className="text-[9px] font-bold uppercase text-slate-400 tracking-wider block mb-2">Architectural Style</label>
            <div className="grid grid-cols-3 gap-1">
              {STYLE_OPTIONS.map(s => (
                <button key={s.id} onClick={() => update("style", s.id)}
                  className={`flex flex-col items-center gap-0.5 py-2 px-1 rounded-xl border text-center transition ${
                    edit.style===s.id
                      ? "border-[#7c93c3] bg-[#7c93c3]/10 text-[#5a73a3]"
                      : "border-slate-100 hover:border-slate-200 text-slate-600"
                  }`}>
                  <span className="text-base">{s.emoji}</span>
                  <span className="text-[7px] font-semibold leading-tight">{s.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Roof */}
          <div>
            <label className="text-[9px] font-bold uppercase text-slate-400 tracking-wider block mb-2">Roof Type</label>
            <div className="grid grid-cols-4 gap-1">
              {ROOF_OPTIONS.map(r => (
                <button key={r.id} onClick={() => update("roof_style", r.id)}
                  className={`flex flex-col items-center gap-0.5 py-1.5 rounded-xl border transition ${
                    edit.roof_style===r.id
                      ? "border-[#7c93c3] bg-[#7c93c3]/10 text-[#5a73a3]"
                      : "border-slate-100 hover:border-slate-200 text-slate-500"
                  }`}>
                  <span className="text-base leading-none">{r.emoji}</span>
                  <span className="text-[7px] font-medium">{r.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Floors */}
          <div>
            <label className="text-[9px] font-bold uppercase text-slate-400 tracking-wider block mb-2">
              Floors — <span className="text-[#7c93c3] font-black">{edit.floors}</span>
            </label>
            <div className="flex items-center gap-2">
              <button onClick={() => update("floors", Math.max(1, edit.floors-1))}
                className="w-8 h-8 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-bold text-sm transition">−</button>
              <input type="range" min={1} max={20} value={edit.floors}
                onChange={e => update("floors", parseInt(e.target.value))}
                className="flex-1 accent-[#7c93c3]"/>
              <button onClick={() => update("floors", Math.min(20, edit.floors+1))}
                className="w-8 h-8 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-bold text-sm transition">+</button>
            </div>
          </div>

        </>)}

        {/* ── INTERIOR ─────────────────────────────────────────── */}
        {section === "interior" && (<>

          {/* Floor material */}
          <div>
            <label className="text-[9px] font-bold uppercase text-slate-400 tracking-wider block mb-2">Floor Material</label>
            <div className="grid grid-cols-4 gap-1.5">
              {FLOOR_MATERIALS.map(m => (
                <button key={m.id} onClick={() => update("floor_material", m.id)}
                  className={`flex flex-col items-center gap-1 py-2 rounded-xl border transition ${
                    edit.floor_material===m.id
                      ? "border-[#7c93c3] shadow-sm"
                      : "border-slate-100 hover:border-slate-200"
                  }`}>
                  <div className="w-8 h-8 rounded-lg border border-slate-200 shadow-sm"
                    style={{ background: m.color }}/>
                  <span className="text-[7px] text-slate-500 font-medium">{m.label}</span>
                  {edit.floor_material===m.id && <Check className="w-2.5 h-2.5 text-[#7c93c3]"/>}
                </button>
              ))}
            </div>
          </div>

          {/* Wall color */}
          <div>
            <label className="text-[9px] font-bold uppercase text-slate-400 tracking-wider block mb-2">Wall Color</label>
            <div className="grid grid-cols-4 gap-1.5">
              {WALL_COLORS.map(c => (
                <button key={c.id} onClick={() => update("wall_color", c.id)}
                  className={`flex flex-col items-center gap-1 py-2 rounded-xl border transition ${
                    edit.wall_color===c.id
                      ? "border-[#7c93c3] shadow-sm"
                      : "border-slate-100 hover:border-slate-200"
                  }`}>
                  <div className="w-8 h-8 rounded-full border border-slate-200 shadow-sm"
                    style={{ background: c.hex }}/>
                  <span className="text-[7px] text-slate-500 font-medium">{c.label}</span>
                  {edit.wall_color===c.id && <Check className="w-2.5 h-2.5 text-[#7c93c3]"/>}
                </button>
              ))}
            </div>
          </div>

          {/* Furniture style */}
          <div>
            <label className="text-[9px] font-bold uppercase text-slate-400 tracking-wider block mb-2">Furniture Style</label>
            <div className="grid grid-cols-2 gap-1.5">
              {FURNITURE_STYLES.map(f => (
                <button key={f.id} onClick={() => update("furniture_style", f.id)}
                  className={`py-2 px-3 rounded-xl border text-[9px] font-semibold transition ${
                    edit.furniture_style===f.id
                      ? "border-[#7c93c3] bg-[#7c93c3]/10 text-[#5a73a3]"
                      : "border-slate-100 text-slate-500 hover:border-slate-200"
                  }`}>{f.label}</button>
              ))}
            </div>
          </div>

        </>)}

        {/* ── FEATURES ─────────────────────────────────────────── */}
        {section === "features" && (<>
          {[
            { key:"balconies" as const, icon:"🌅", label:"Balconies",        desc:"Add balconies on all upper floors" },
            { key:"pool"      as const, icon:"🏊", label:"Swimming Pool",    desc:"Pool on the right side with deck" },
            { key:"garage"    as const, icon:"🚗", label:"Garage",           desc:"2-car garage with overhead doors" },
          ].map(f => (
            <button key={f.key} onClick={() => update(f.key, !edit[f.key])}
              className={`w-full flex items-center gap-3 p-3 rounded-xl border transition text-left ${
                edit[f.key]
                  ? "border-[#7c93c3] bg-[#7c93c3]/8"
                  : "border-slate-100 hover:border-slate-200"
              }`}>
              <span className="text-xl flex-shrink-0">{f.icon}</span>
              <div className="flex-1">
                <p className={`text-[10px] font-bold ${edit[f.key]?"text-[#5a73a3]":"text-slate-700"}`}>{f.label}</p>
                <p className="text-[8px] text-slate-400">{f.desc}</p>
              </div>
              <div className={`w-8 h-4.5 rounded-full transition flex items-center px-0.5 ${
                edit[f.key] ? "bg-[#7c93c3] justify-end" : "bg-slate-200 justify-start"
              }`}>
                <div className="w-3.5 h-3.5 rounded-full bg-white shadow-sm"/>
              </div>
            </button>
          ))}

          <div className="mt-4 bg-slate-50 rounded-xl p-3 border border-slate-100">
            <p className="text-[9px] text-slate-400 text-center">
              Toggle features then tap <strong className="text-[#7c93c3]">Regenerate</strong> to rebuild with changes
            </p>
          </div>
        </>)}

      </div>

      {/* Regenerate footer */}
      <div className="border-t border-slate-100 p-3 bg-white sticky bottom-0">
        <button onClick={regenerate} disabled={regen}
          className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-xs transition ${
            changed
              ? "bg-[#7c93c3] hover:bg-[#8da3d3] text-white shadow-md shadow-[#7c93c3]/20"
              : "bg-slate-100 text-slate-400 cursor-not-allowed"
          }`}>
          {regen
            ? <><Loader2 className="w-3.5 h-3.5 animate-spin"/> Regenerating…</>
            : <><RefreshCw className="w-3.5 h-3.5"/> {changed ? "Apply Changes & Regenerate" : "No Changes"}</>
          }
        </button>
      </div>
    </div>
  );
}
