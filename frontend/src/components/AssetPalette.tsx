"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useStore } from "@/lib/store";
import { Search, Layers, TreePine, Sofa, Armchair, Lamp, Upload, X, GripVertical } from "lucide-react";

// ====================================================
// TYPES
// ====================================================

interface SketchfabAsset {
  uid: string;
  name: string;
  thumbnail: string;
  author: string;
  is_downloadable: boolean;
  tags: string[];
}

interface CatalogItem {
  query: string;
  category: string | null;
}

// ====================================================
// ASSET PALETTE — Sidebar with drag-and-drop source
// ====================================================

export default function AssetPalette() {
  const [activeTab, setActiveTab] = useState<"interior" | "exterior">("interior");
  const [activeRoom, setActiveRoom] = useState("living");
  const [searchQuery, setSearchQuery] = useState("");
  const [assets, setAssets] = useState<SketchfabAsset[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [draggingAsset, setDraggingAsset] = useState<SketchfabAsset | null>(null);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://ai-architect-production-1e57.up.railway.app";

  // Fetch catalog or search results
  const fetchAssets = useCallback(async () => {
    setIsLoading(true);
    try {
      let url: string;
      let body: any;

      if (searchQuery.trim()) {
        url = `${API_BASE}/api/assets/search`;
        body = {
          query: searchQuery,
          context: activeTab,
          max_results: 24
        };
      } else {
        url = `${API_BASE}/api/assets/catalog/${activeRoom}`;
        const resp = await fetch(url);
        const data = await resp.json();
        // Search each catalog item
        const allResults: SketchfabAsset[] = [];
        for (const item of data.items || []) {
          const searchResp = await fetch(`${API_BASE}/api/assets/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              query: item.query,
              category: item.category,
              context: activeTab,
              max_results: 4
            })
          });
          const searchData = await searchResp.json();
          allResults.push(...searchData);
        }
        setAssets(allResults.slice(0, 24));
        setIsLoading(false);
        return;
      }

      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const data = await resp.json();
      setAssets(data);
    } catch (e) {
      console.error("Asset fetch error:", e);
    }
    setIsLoading(false);
  }, [searchQuery, activeTab, activeRoom, API_BASE]);

  useEffect(() => {
    fetchAssets();
  }, [fetchAssets]);

  // Handle drag start
  const handleDragStart = (e: React.DragEvent, asset: SketchfabAsset) => {
    setDraggingAsset(asset);

    const payload = JSON.stringify({
      uid: asset.uid,
      name: asset.name,
      source: "sketchfab"
    });

    // Primary: HTML5 dataTransfer (read by ThreeJSViewer onDrop)
    e.dataTransfer.setData("application/json", payload);
    e.dataTransfer.setData("text/plain", payload); // fallback for some browsers
    e.dataTransfer.effectAllowed = "copy";

    // Also store on window as belt-and-suspenders fallback
    (window as any).__draggedAsset = { uid: asset.uid, name: asset.name, source: "sketchfab" };

    // Drag image from thumbnail
    if (asset.thumbnail) {
      const img = new Image();
      img.src = asset.thumbnail;
      e.dataTransfer.setDragImage(img, 32, 32);
    }
  };

  const handleDragEnd = () => {
    setDraggingAsset(null);
  };

  const interiorRooms = [
    { id: "living", label: "Living Room", icon: Sofa },
    { id: "bedroom", label: "Bedroom", icon: Armchair },
    { id: "kitchen", label: "Kitchen", icon: Lamp },
    { id: "bathroom", label: "Bathroom", icon: Layers }
  ];

  const exteriorRooms = [
    { id: "landscape", label: "Landscape", icon: TreePine },
    { id: "facade", label: "Facade", icon: Layers },
    { id: "outdoor", label: "Outdoor", icon: Sofa }
  ];

  const rooms = activeTab === "interior" ? interiorRooms : exteriorRooms;

  return (
    <div className="w-80 h-full bg-neutral-900 border-r border-neutral-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-neutral-700">
        <h2 className="text-sm font-semibold text-white mb-3">Asset Library</h2>

        {/* Tab Switch */}
        <div className="flex bg-neutral-800 rounded-lg p-1 mb-3">
          <button
            onClick={() => setActiveTab("interior")}
            className={`flex-1 py-1.5 text-xs rounded-md transition ${
              activeTab === "interior" ? "bg-blue-600 text-white" : "text-neutral-400 hover:text-white"
            }`}
          >
            Interior
          </button>
          <button
            onClick={() => setActiveTab("exterior")}
            className={`flex-1 py-1.5 text-xs rounded-md transition ${
              activeTab === "exterior" ? "bg-emerald-600 text-white" : "text-neutral-400 hover:text-white"
            }`}
          >
            Exterior
          </button>
        </div>

        {/* Room Selector */}
        <div className="flex gap-1.5 flex-wrap">
          {rooms.map((room) => {
            const Icon = room.icon;
            return (
              <button
                key={room.id}
                onClick={() => setActiveRoom(room.id)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs transition ${
                  activeRoom === room.id
                    ? activeTab === "interior"
                      ? "bg-blue-600/20 text-blue-400 border border-blue-600/40"
                      : "bg-emerald-600/20 text-emerald-400 border border-emerald-600/40"
                    : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                }`}
              >
                <Icon size={12} />
                {room.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-neutral-700">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-500" />
          <input
            type="text"
            placeholder="Search Sketchfab..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-neutral-800 text-white text-xs pl-8 pr-3 py-2 rounded-md border border-neutral-700 focus:border-blue-500 focus:outline-none"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-white"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Asset Grid */}
      <div className="flex-1 overflow-y-auto p-3">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full" />
          </div>
        ) : assets.length === 0 ? (
          <div className="text-center py-8 text-neutral-500 text-xs">
            No assets found. Try a different search.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            {assets.map((asset) => (
              <div
                key={asset.uid}
                draggable
                onDragStart={(e) => handleDragStart(e, asset)}
                onDragEnd={handleDragEnd}
                className={`group relative bg-neutral-800 rounded-lg overflow-hidden cursor-grab active:cursor-grabbing hover:ring-2 hover:ring-blue-500/50 transition ${
                  draggingAsset?.uid === asset.uid ? "opacity-50" : ""
                }`}
              >
                {/* Thumbnail */}
                <div className="aspect-square bg-neutral-700 relative">
                  {asset.thumbnail ? (
                    <img
                      src={asset.thumbnail}
                      alt={asset.name}
                      className="w-full h-full object-cover"
                      draggable={false}
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-neutral-600">
                      <Layers size={20} />
                    </div>
                  )}
                  {/* Drag Handle */}
                  <div className="absolute top-1 right-1 bg-black/60 rounded p-1 opacity-0 group-hover:opacity-100 transition">
                    <GripVertical size={10} className="text-white" />
                  </div>
                  {/* Downloadable Badge */}
                  {asset.is_downloadable && (
                    <div className="absolute bottom-1 left-1 bg-green-600/80 text-white text-[9px] px-1.5 py-0.5 rounded">
                      GLB
                    </div>
                  )}
                </div>
                {/* Info */}
                <div className="p-2">
                  <p className="text-[10px] text-white truncate font-medium">{asset.name}</p>
                  <p className="text-[9px] text-neutral-500 truncate">{asset.author}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload Zone */}
      <div className="p-3 border-t border-neutral-700">
        <label className="flex items-center justify-center gap-2 w-full py-2.5 bg-neutral-800 hover:bg-neutral-700 rounded-lg cursor-pointer transition text-xs text-neutral-400 hover:text-white">
          <Upload size={14} />
          Upload GLB / OBJ
          <input
            type="file"
            accept=".glb,.gltf,.obj,.fbx"
            className="hidden"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              const formData = new FormData();
              formData.append("file", file);
              formData.append("room_type", activeRoom);
              formData.append("name", file.name);
              try {
                const resp = await fetch(`${API_BASE}/api/assets/upload`, {
                  method: "POST",
                  body: formData
                });
                const data = await resp.json();
                if (data.ready) {
                  // Add to local assets immediately
                  setAssets(prev => [{
                    uid: data.uid,
                    name: data.name,
                    thumbnail: "",
                    author: "You",
                    is_downloadable: true,
                    tags: []
                  }, ...prev]);
                }
              } catch (err) {
                console.error("Upload failed:", err);
              }
            }}
          />
        </label>
      </div>
    </div>
  );
}
