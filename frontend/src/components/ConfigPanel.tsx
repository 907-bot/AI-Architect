"use client";
import React from "react";
import { Palette, Layers, Sun, Car, Flower2 } from "lucide-react";

export default function ConfigPanel({ config, setConfig }: { config: any; setConfig: (c: any) => void }) {
  const wallColors = [
    { id: "white", name: "White", hex: "#f5f5f0" },
    { id: "cream", name: "Cream", hex: "#d9d0c1" },
    { id: "red", name: "Red Brick", hex: "#a0522d" },
    { id: "dark", name: "Dark", hex: "#4a4036" },
  ];
  const roofStyles = [
    { id: "gable", name: "Gabled" },
    { id: "flat", name: "Flat" },
    { id: "hip", name: "Hip" },
  ];
  const glassTypes = [
    { id: "clear", name: "Clear", hex: "#d0e8f0" },
    { id: "tinted", name: "Tinted", hex: "#405060" },
    { id: "reflective", name: "Reflective", hex: "#6080a0" },
  ];
  return (
    <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-4 shadow-lg border border-slate-200/50">
      <div className="flex items-center gap-2 mb-4">
        <Palette className="w-4 h-4 text-slate-600" />
        <h3 className="text-sm font-semibold text-slate-700">Exterior Options</h3>
      </div>
      <div className="mb-4">
        <label className="text-xs text-slate-500 mb-2 block">Wall Color</label>
        <div className="flex gap-2">
          {wallColors.map((c) => (
            <button key={c.id} onClick={() => setConfig({ ...config, wallColor: c.id })}
              className={`w-8 h-8 rounded-full border-2 transition-all ${config.wallColor === c.id ? "border-blue-500 scale-110" : "border-slate-300"}`}
              style={{ backgroundColor: c.hex }} title={c.name} />
          ))}
        </div>
      </div>
      <div className="mb-4">
        <label className="text-xs text-slate-500 mb-2 block">Roof Style</label>
        <div className="flex gap-2">
          {roofStyles.map((r) => (
            <button key={r.id} onClick={() => setConfig({ ...config, roofStyle: r.id })}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium ${config.roofStyle === r.id ? "bg-blue-500 text-white" : "bg-slate-100 text-slate-600"}`}>
              {r.name}
            </button>
          ))}
        </div>
      </div>
      <div className="mb-4">
        <label className="text-xs text-slate-500 mb-2 block">Window Glass</label>
        <div className="flex gap-2">
          {glassTypes.map((g) => (
            <button key={g.id} onClick={() => setConfig({ ...config, windowGlass: g.id })}
              className={`w-8 h-8 rounded-lg border-2 ${config.windowGlass === g.id ? "border-blue-500" : "border-slate-300"}`}
              style={{ backgroundColor: g.hex + "80" }} title={g.name} />
          ))}
        </div>
      </div>
      <div className="mb-4">
        <label className="text-xs text-slate-500 mb-2 block">Floors: {config.floors}</label>
        <input type="range" min="1" max="10" value={config.floors}
          onChange={(e) => setConfig({ ...config, floors: parseInt(e.target.value) })} className="w-full accent-blue-500" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <button onClick={() => setConfig({ ...config, balcony: !config.balcony })}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${config.balcony ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600"}`}>
          <Layers className="w-3.5 h-3.5" /> Balcony
        </button>
        <button onClick={() => setConfig({ ...config, garage: !config.garage })}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${config.garage ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600"}`}>
          <Car className="w-3.5 h-3.5" /> Garage
        </button>
        <button onClick={() => setConfig({ ...config, pool: !config.pool })}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${config.pool ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600"}`}>
          <Sun className="w-3.5 h-3.5" /> Pool
        </button>
        <button onClick={() => setConfig({ ...config, garden: !config.garden })}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${config.garden ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-600"}`}>
          <Flower2 className="w-3.5 h-3.5" /> Garden
        </button>
      </div>
      <button onClick={() => {
        let prompt = config.floors + " floored";
        if (config.wallColor !== "white") prompt += " " + config.wallColor;
        if (config.balcony) prompt += " with balcony";
        if (config.garage) prompt += " with garage";
        if (config.pool) prompt += " with pool";
        if (config.garden) prompt += " with garden";
        prompt += " house";
        window.dispatchEvent(new CustomEvent("build-config", { detail: prompt }));
      }} className="w-full mt-4 py-2.5 bg-[#7c93c3] hover:bg-[#8da3d3] text-white rounded-xl text-sm font-medium">
        Build Now
      </button>
    </div>
  );
}