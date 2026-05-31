"use client";
import React, { useState } from "react";

export const STYLES = [
  // ── Modern & Contemporary ─────────────────────────────────────────────────
  { id:"modern",         cat:"Modern",     label:"Modern",           emoji:"🏢", desc:"Flat roof · glass · concrete" },
  { id:"contemporary",   cat:"Modern",     label:"Contemporary",     emoji:"🔷", desc:"Bold forms · large windows · steel" },
  { id:"minimalist",     cat:"Modern",     label:"Minimalist",       emoji:"⬜", desc:"Clean lines · neutral palette · void" },
  { id:"bauhaus",        cat:"Modern",     label:"Bauhaus",          emoji:"📐", desc:"Geometric · functional · no ornament" },
  { id:"mid_century",    cat:"Modern",     label:"Mid-Century Modern",emoji:"🛋️", desc:"Flat/shed roof · open plan · organic" },
  { id:"deconstructivist",cat:"Modern",   label:"Deconstructivist",  emoji:"💠", desc:"Angular · fragmented · Gehry style" },
  { id:"high_tech",      cat:"Modern",     label:"High-Tech",        emoji:"⚙️",  desc:"Exposed structure · Pompidou style" },
  { id:"parametric",     cat:"Modern",     label:"Parametric",       emoji:"🌀", desc:"Algorithmic forms · Zaha Hadid" },
  // ── Asian ─────────────────────────────────────────────────────────────────
  { id:"japanese",       cat:"Asian",      label:"Japanese",         emoji:"⛩️",  desc:"Pagoda roof · zen · wood · engawa" },
  { id:"japanese_modern",cat:"Asian",      label:"Japanese Modern",  emoji:"🎋", desc:"Wabi-sabi · clean · natural light" },
  { id:"chinese",        cat:"Asian",      label:"Chinese",          emoji:"🏯", desc:"Curved roof · red columns · ornate" },
  { id:"korean",         cat:"Asian",      label:"Korean Hanok",     emoji:"🇰🇷", desc:"Curved eaves · natural materials" },
  { id:"thai",           cat:"Asian",      label:"Thai",             emoji:"🛕", desc:"Layered spired roofs · gold accent" },
  { id:"balinese",       cat:"Asian",      label:"Balinese",         emoji:"🌺", desc:"Thatched · stone carvings · tropical" },
  { id:"vietnamese",     cat:"Asian",      label:"Vietnamese",       emoji:"🏮", desc:"Tube house · colourful · balconies" },
  // ── South Asian ───────────────────────────────────────────────────────────
  { id:"mughal",         cat:"South Asian",label:"Mughal",           emoji:"🕌", desc:"Domes · arches · white marble · Taj" },
  { id:"dravidian",      cat:"South Asian",label:"Dravidian",        emoji:"🪔", desc:"Tiered gopuram · vibrant · stone" },
  { id:"rajasthani",     cat:"South Asian",label:"Rajasthani",       emoji:"🏰", desc:"Jharokha windows · sandstone · jali" },
  { id:"kerala",         cat:"South Asian",label:"Kerala Traditional",emoji:"🌴", desc:"Sloped roof · teak · nalukettu" },
  { id:"indo_modern",    cat:"South Asian",label:"Indo-Modern",      emoji:"✨", desc:"Contemporary + Indian elements" },
  // ── Mediterranean & European ──────────────────────────────────────────────
  { id:"villa",          cat:"European",   label:"Mediterranean Villa",emoji:"🏡", desc:"Hip roof · terracotta · arches" },
  { id:"italian",        cat:"European",   label:"Italian Renaissance",emoji:"🇮🇹", desc:"Loggia · rusticated · classical" },
  { id:"french_chateau", cat:"European",   label:"French Château",   emoji:"🗼", desc:"Mansard roof · dormer · Loire valley" },
  { id:"spanish",        cat:"European",   label:"Spanish Hacienda",  emoji:"🇪🇸", desc:"Courtyard · white plaster · bougainvillea" },
  { id:"greek",          cat:"European",   label:"Greek",            emoji:"🏛️", desc:"White cubic · blue dome · Santorini" },
  { id:"turkish",        cat:"European",   label:"Ottoman Turkish",   emoji:"🕌", desc:"Domes · minarets · geometric tiles" },
  { id:"scandinavian",   cat:"European",   label:"Scandinavian",      emoji:"🏔️", desc:"Steep gable · light wood · minimal" },
  { id:"victorian",      cat:"European",   label:"Victorian",         emoji:"🎠", desc:"Bay windows · ornate trim · steep gable" },
  { id:"georgian",       cat:"European",   label:"Georgian",          emoji:"🇬🇧", desc:"Symmetrical · sash windows · brick" },
  { id:"classical",      cat:"European",   label:"Neoclassical",      emoji:"🏺", desc:"Columns · marble · pediment" },
  // ── Middle Eastern & African ─────────────────────────────────────────────
  { id:"moroccan",       cat:"Middle East",label:"Moroccan Riad",    emoji:"🧱", desc:"Courtyard · zellige tiles · keyhole arch" },
  { id:"persian",        cat:"Middle East",label:"Persian",          emoji:"🌹", desc:"Iwan portal · muqarnas · blue tile" },
  { id:"arabic",         cat:"Middle East",label:"Arabic",           emoji:"☪️",  desc:"Wind tower · mashrabiya screens" },
  { id:"cape_dutch",     cat:"Africa",     label:"Cape Dutch",       emoji:"🇿🇦", desc:"Curved gable · whitewashed · Cape Malay" },
  // ── Americas ─────────────────────────────────────────────────────────────
  { id:"colonial",       cat:"Americas",   label:"American Colonial", emoji:"🇺🇸", desc:"White columns · gable · symmetrical" },
  { id:"craftsman",      cat:"Americas",   label:"Craftsman Bungalow",emoji:"🪵", desc:"Low pitched · natural · porch" },
  { id:"ranch",          cat:"Americas",   label:"Ranch House",       emoji:"🤠", desc:"Single storey · wide · attached garage" },
  { id:"prairie",        cat:"Americas",   label:"Prairie (F.L.Wright)",emoji:"🌾", desc:"Horizontal lines · overhanging eaves" },
  { id:"brazilian",      cat:"Americas",   label:"Brazilian Modernist",emoji:"🇧🇷", desc:"Pilotis · Niemeyer · curvilinear" },
  { id:"mexican",        cat:"Americas",   label:"Mexican Hacienda",  emoji:"🌵", desc:"Courtyard · terracotta · painted walls" },
  // ── Industrial & Special ─────────────────────────────────────────────────
  { id:"industrial",     cat:"Special",    label:"Industrial",        emoji:"🏭", desc:"Exposed brick · steel beams · loft" },
  { id:"brutalist",      cat:"Special",    label:"Brutalist",         emoji:"🧱", desc:"Raw concrete · monolithic · geometric" },
  { id:"earthship",      cat:"Special",    label:"Earthship",         emoji:"🌍", desc:"Rammed earth · passive · off-grid" },
  { id:"tiny_house",     cat:"Special",    label:"Tiny House",        emoji:"🏠", desc:"Compact · clever storage · mobile" },
  { id:"treehouse",      cat:"Special",    label:"Treehouse",         emoji:"🌳", desc:"Elevated · natural integration · fun" },
  { id:"futuristic",     cat:"Special",    label:"Futuristic",        emoji:"🚀", desc:"Organic curves · smart home · AI-designed" },
];

const CATEGORIES = [...new Set(STYLES.map(s => s.cat))];

interface StylePickerProps { selected: string; onChange: (style: string) => void; }

export default function StylePicker({ selected, onChange }: StylePickerProps) {
  const [activeCat, setActiveCat] = useState("Modern");

  const filtered = STYLES.filter(s => s.cat === activeCat);
  const selectedStyle = STYLES.find(s => s.id === selected);

  return (
    <div className="px-3 py-2">
      <div className="flex items-center justify-between mb-2 px-1">
        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400">
          Architectural Style
        </p>
        {selectedStyle && selectedStyle.cat !== activeCat && (
          <span className="text-[9px] text-[#7c93c3] font-medium">
            {selectedStyle.emoji} {selectedStyle.label}
          </span>
        )}
      </div>

      {/* Category tabs */}
      <div className="flex flex-wrap gap-1 mb-2">
        {CATEGORIES.map(cat => (
          <button key={cat} onClick={() => setActiveCat(cat)}
            className={`px-2 py-0.5 rounded-full text-[8px] font-semibold transition ${
              activeCat === cat
                ? "bg-[#7c93c3] text-white"
                : "bg-slate-100 text-slate-500 hover:bg-slate-200"
            }`}>
            {cat}
          </button>
        ))}
      </div>

      {/* Style grid */}
      <div className="grid grid-cols-2 gap-1">
        {filtered.map(s => {
          const active = selected === s.id;
          return (
            <button key={s.id} onClick={() => onChange(s.id)}
              className={`flex items-start gap-1.5 rounded-lg px-2 py-1.5 text-left transition border ${
                active
                  ? "bg-[#7c93c3]/15 border-[#7c93c3]/50 shadow-sm"
                  : "bg-white border-slate-100 hover:border-slate-200 hover:bg-slate-50"
              }`}>
              <span className="text-sm leading-none mt-0.5 flex-shrink-0">{s.emoji}</span>
              <div className="min-w-0">
                <p className={`text-[9px] font-bold leading-tight truncate ${active?"text-[#5a73a3]":"text-slate-700"}`}>
                  {s.label}
                </p>
                <p className="text-[7px] text-slate-400 leading-tight mt-0.5 truncate">{s.desc}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
