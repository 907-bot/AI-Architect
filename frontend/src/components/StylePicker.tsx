"use client";
import React from "react";

export const STYLES = [
  { id:"modern",       label:"Modern",       emoji:"🏢", desc:"Flat roof, glass & concrete",        color:"#475569" },
  { id:"japanese",     label:"Japanese",     emoji:"⛩️",  desc:"Pagoda roof, zen garden, wood",      color:"#8b5e3c" },
  { id:"villa",        label:"Villa",        emoji:"🏡", desc:"Hip roof, terracotta, arches",        color:"#c2680a" },
  { id:"asian",        label:"Asian",        emoji:"🏯", desc:"Curved roof, red columns, ornate",   color:"#b91c1c" },
  { id:"scandinavian", label:"Scandinavian", emoji:"🏔️", desc:"Steep gable, light wood, minimal",   color:"#0c4a6e" },
  { id:"industrial",   label:"Industrial",   emoji:"🏭", desc:"Exposed brick, steel beams, loft",  color:"#374151" },
  { id:"colonial",     label:"Colonial",     emoji:"🏛️", desc:"White columns, gable roof, classic", color:"#1e40af" },
  { id:"classical",    label:"Classical",    emoji:"🏺", desc:"Marble, portico, neoclassical",      color:"#713f12" },
];

interface StylePickerProps {
  selected: string;
  onChange: (style: string) => void;
}

export default function StylePicker({ selected, onChange }: StylePickerProps) {
  return (
    <div className="px-3 py-2">
      <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-2 px-1">
        Architectural Style
      </p>
      <div className="grid grid-cols-2 gap-1.5">
        {STYLES.map((s) => {
          const active = selected === s.id;
          return (
            <button key={s.id} onClick={() => onChange(s.id)}
              className={`flex items-start gap-2 rounded-xl px-2.5 py-2 text-left transition-all border ${
                active
                  ? "bg-[#7c93c3]/15 border-[#7c93c3]/50 shadow-sm"
                  : "bg-white border-slate-100 hover:border-slate-200 hover:bg-slate-50"
              }`}>
              <span className="text-lg leading-none mt-0.5">{s.emoji}</span>
              <div>
                <p className={`text-[10px] font-bold leading-tight ${active ? "text-[#5a73a3]" : "text-slate-700"}`}>
                  {s.label}
                </p>
                <p className="text-[8px] text-slate-400 leading-tight mt-0.5">{s.desc}</p>
              </div>
              {active && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0"
                  style={{ background: s.color }} />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
