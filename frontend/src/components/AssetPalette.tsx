"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Search, X, GripVertical, Upload, Sofa, TreePine,
  Layers, Armchair, ChefHat, Bath, Loader2, Package,
  ExternalLink, AlertCircle,
} from "lucide-react";

// ─── Types ─────────────────────────────────────────────────────────────────────

interface SketchfabAsset {
  uid: string;
  name: string;
  thumbnail: string;
  author: string;
  is_downloadable: boolean;
  tags: string[];
  embed_url?: string;
}

const API_BASE = "https://ai-architect-production-1e57.up.railway.app";

// Fallback: query Sketchfab public search directly from browser (no auth needed)
async function searchSketchfabDirect(query: string, count = 20): Promise<SketchfabAsset[]> {
  try {
    const url = `https://api.sketchfab.com/v3/models?q=${encodeURIComponent(query)}&count=${count}&sort_by=relevance&downloadable=true`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Sketchfab API error");
    const data = await res.json();
    return (data.results || []).map((m: any) => ({
      uid: m.uid,
      name: m.name || "Untitled",
      thumbnail: m.thumbnails?.images?.[0]?.url || "",
      author: m.user?.displayName || "Unknown",
      is_downloadable: m.isDownloadable ?? false,
      tags: (m.tags || []).map((t: any) => t.name || t),
      embed_url: `https://sketchfab.com/models/${m.uid}/embed?autospin=0&autostart=0`,
    }));
  } catch {
    return [];
  }
}

// ─── Room catalog ──────────────────────────────────────────────────────────────

const CATALOG = {
  interior: {
    living:   { icon: Sofa,    label: "Living",   queries: ["modern sofa", "coffee table", "floor lamp", "tv stand", "rug carpet"] },
    bedroom:  { icon: Armchair,label: "Bedroom",  queries: ["double bed", "wardrobe", "nightstand", "dresser mirror", "table lamp"] },
    kitchen:  { icon: ChefHat, label: "Kitchen",  queries: ["refrigerator", "kitchen stove", "dining table", "kitchen island", "sink faucet"] },
    bathroom: { icon: Bath,    label: "Bathroom", queries: ["toilet", "shower cabin", "bathroom vanity", "bathtub freestanding", "towel rack"] },
  },
  exterior: {
    landscape:{ icon: TreePine,label: "Landscape",queries: ["realistic tree", "bush hedge", "flower pot", "garden bench", "fountain"] },
    outdoor:  { icon: Sofa,    label: "Outdoor",  queries: ["outdoor chair", "bbq grill", "patio table", "parasol umbrella", "planter box"] },
    facade:   { icon: Layers,  label: "Facade",   queries: ["front door", "balcony railing", "window frame", "garage door", "awning canopy"] },
  },
};

// ─── AssetCard ────────────────────────────────────────────────────────────────

function AssetCard({ asset, onDragStart }: { asset: SketchfabAsset; onDragStart: (e: React.DragEvent, a: SketchfabAsset) => void }) {
  const [imgOk, setImgOk] = useState(true);

  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, asset)}
      className="group relative bg-white border border-slate-200 rounded-xl overflow-hidden cursor-grab active:cursor-grabbing hover:border-[#7c93c3] hover:shadow-md transition-all duration-150"
      title={`${asset.name} — drag to scene`}
    >
      {/* Thumbnail */}
      <div className="aspect-square bg-slate-100 relative overflow-hidden">
        {asset.thumbnail && imgOk ? (
          <img
            src={asset.thumbnail}
            alt={asset.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            draggable={false}
            onError={() => setImgOk(false)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Package className="w-8 h-8 text-slate-300" />
          </div>
        )}
        {/* Drag handle hint */}
        <div className="absolute inset-0 bg-[#7c93c3]/0 group-hover:bg-[#7c93c3]/10 transition-colors flex items-center justify-center">
          <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-white/90 rounded-lg px-2 py-1 text-[9px] font-medium text-slate-600 flex items-center gap-1">
            <GripVertical className="w-3 h-3" />Drag to scene
          </div>
        </div>
        {asset.is_downloadable && (
          <div className="absolute top-1.5 right-1.5 bg-emerald-500 text-white text-[8px] font-bold px-1.5 py-0.5 rounded-full">
            GLB
          </div>
        )}
      </div>
      {/* Info */}
      <div className="p-2">
        <p className="text-[10px] font-semibold text-slate-700 truncate">{asset.name}</p>
        <p className="text-[9px] text-slate-400 truncate">{asset.author}</p>
      </div>
    </div>
  );
}

// ─── Main palette ─────────────────────────────────────────────────────────────

export default function AssetPalette({ onClose }: { onClose?: () => void }) {
  const [tab, setTab] = useState<"interior" | "exterior">("interior");
  const [room, setRoom] = useState("living");
  const [search, setSearch] = useState("");
  const [assets, setAssets] = useState<SketchfabAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Ensure selected room exists in current tab
  useEffect(() => {
    const rooms = Object.keys(CATALOG[tab]);
    if (!rooms.includes(room)) setRoom(rooms[0]);
  }, [tab, room]);

  const loadAssets = useCallback(async (q: string, roomKey: string, tabKey: "interior" | "exterior") => {
    setLoading(true);
    setApiError(false);
    try {
      let results: SketchfabAsset[] = [];

      if (q.trim()) {
        // Use Sketchfab directly for free-text search
        results = await searchSketchfabDirect(q, 24);
      } else {
        // Load first query from catalog (most representative)
        const catalog = CATALOG[tabKey] as any;
        const entry = catalog[roomKey];
        if (entry) {
          results = await searchSketchfabDirect(entry.queries[0], 24);
        }
      }

      setAssets(results);
      if (results.length === 0) setApiError(true);
    } catch {
      setApiError(true);
    }
    setLoading(false);
  }, []);

  // Debounce search
  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => loadAssets(search, room, tab), 400);
    return () => clearTimeout(debounceRef.current);
  }, [search, room, tab, loadAssets]);

  const handleDragStart = (e: React.DragEvent, asset: SketchfabAsset) => {
    e.dataTransfer.setData("application/json", JSON.stringify({
      uid: asset.uid,
      name: asset.name,
      thumbnail: asset.thumbnail,
      author: asset.author,
      source: "sketchfab",
      embed_url: asset.embed_url,
      room_context: room,
      tab_context: tab,
    }));
    e.dataTransfer.effectAllowed = "copy";
  };

  const rooms = CATALOG[tab] as any;

  return (
    <div className="w-[280px] h-full flex flex-col bg-white border-r border-slate-200 shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
        <div>
          <h2 className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
            <Package className="w-3.5 h-3.5 text-[#7c93c3]" />
            Asset Library
          </h2>
          <p className="text-[9px] text-slate-400 mt-0.5">Powered by Sketchfab • Drag to 3D scene</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition">
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Interior / Exterior tabs */}
      <div className="flex bg-slate-50 m-3 rounded-lg p-0.5 border border-slate-200">
        {(["interior", "exterior"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-1.5 rounded-md text-[10px] font-semibold transition capitalize ${
              tab === t ? "bg-white shadow-sm text-[#7c93c3] border border-slate-200" : "text-slate-500 hover:text-slate-700"
            }`}
          >{t}</button>
        ))}
      </div>

      {/* Room tabs */}
      <div className="flex gap-1 px-3 pb-2 overflow-x-auto scrollbar-hide">
        {Object.entries(rooms).map(([key, val]: any) => {
          const Icon = val.icon;
          return (
            <button
              key={key}
              onClick={() => setRoom(key)}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[9px] font-medium whitespace-nowrap transition border ${
                room === key
                  ? tab === "interior"
                    ? "bg-[#7c93c3]/15 text-[#5a6e9c] border-[#7c93c3]/40"
                    : "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : "bg-white text-slate-500 border-slate-200 hover:border-slate-300 hover:text-slate-700"
              }`}
            >
              <Icon className="w-3 h-3" />
              {val.label}
            </button>
          );
        })}
      </div>

      {/* Search */}
      <div className="px-3 pb-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder={`Search ${tab} assets…`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-8 py-2 text-[11px] text-slate-700 placeholder-slate-400 outline-none focus:border-[#7c93c3] focus:ring-1 focus:ring-[#7c93c3]/20 transition"
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Asset grid */}
      <div className="flex-1 overflow-y-auto px-3 pb-3">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-32 gap-2 text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin text-[#7c93c3]" />
            <p className="text-[10px]">Loading from Sketchfab…</p>
          </div>
        ) : apiError ? (
          <div className="flex flex-col items-center justify-center h-32 gap-2 text-slate-400 px-4 text-center">
            <AlertCircle className="w-5 h-5 text-amber-400" />
            <p className="text-[10px]">Couldn't load assets. Check your internet connection.</p>
            <button onClick={() => loadAssets(search, room, tab)}
              className="text-[10px] text-[#7c93c3] hover:underline">Retry</button>
          </div>
        ) : assets.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 gap-2 text-slate-400 text-center">
            <Package className="w-5 h-5" />
            <p className="text-[10px]">No assets found. Try a different search.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            {assets.map((asset) => (
              <AssetCard key={asset.uid} asset={asset} onDragStart={handleDragStart} />
            ))}
          </div>
        )}
      </div>

      {/* Upload your own */}
      <div className="px-3 py-3 border-t border-slate-100">
        <label className="flex items-center justify-center gap-2 w-full py-2.5 bg-slate-50 hover:bg-slate-100 border border-dashed border-slate-300 hover:border-[#7c93c3] rounded-xl cursor-pointer transition text-[10px] text-slate-500 hover:text-slate-700">
          <Upload className="w-3.5 h-3.5" />
          Upload your GLB / OBJ model
          <input type="file" accept=".glb,.gltf,.obj,.fbx" className="hidden"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              // Dispatch as a custom drag-drop event so ThreeJSViewer picks it up
              window.dispatchEvent(new CustomEvent("asset-upload", {
                detail: { name: file.name, uid: `upload-${Date.now()}`, source: "upload", file }
              }));
            }}
          />
        </label>
        <p className="text-center text-[9px] text-slate-400 mt-1.5">
          <ExternalLink className="w-2.5 h-2.5 inline mr-0.5" />
          <a href="https://sketchfab.com/search?type=models&downloadable=true" target="_blank" rel="noopener noreferrer" className="hover:text-[#7c93c3]">Browse more on Sketchfab</a>
        </p>
      </div>
    </div>
  );
}
