"use client";

import React, { useState } from "react";
import { Search, Loader2, Sparkles } from "lucide-react";
import { useStore } from "@/lib/store";

export default function SemanticSearch() {
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [semanticResults, setSemanticResults] = useState<any[]>([]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    // Mock local query search or index matching
    setTimeout(() => {
      const mockMatches = [
        { name: "Oak Wood Ceiling Slab", desc: "Top floor aesthetic insulation slab", confidence: 0.94 },
        { name: "Plaster Wall Structure", desc: "Solid layout outer partitions", confidence: 0.81 }
      ].filter(item => item.name.toLowerCase().includes(query.toLowerCase()) || item.desc.toLowerCase().includes(query.toLowerCase()));
      
      setSemanticResults(mockMatches);
      setIsSearching(false);
    }, 800);
  };

  return (
    <div className="glass-panel p-4 rounded-xl space-y-3">
      <div className="flex items-center gap-2 text-slate-700">
        <Search className="w-4 h-4 text-slate-500" />
        <h3 className="text-xs font-semibold tracking-wide uppercase font-outfit">
          Semantic Scene Search
        </h3>
      </div>

      <form onSubmit={handleSearch} className="relative flex items-center">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. where is the wood roof?"
          className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 pl-3 pr-9 text-xs text-slate-800 placeholder-slate-400 outline-none focus:border-slate-400 transition duration-150"
        />
        <button type="submit" className="absolute right-2 text-slate-400 hover:text-slate-600">
          {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
        </button>
      </form>

      {semanticResults.length > 0 && (
        <div className="space-y-2 mt-2 pt-2 border-t border-slate-100 max-h-36 overflow-y-auto">
          {(semanticResults || []).map((res, i) => (
            <div key={i} className="p-2 rounded bg-slate-50/50 border border-slate-100 text-[11px]">
              <div className="flex justify-between font-semibold text-slate-700">
                <span>{res.name}</span>
                <span className="text-[#7c93c3]">{(res.confidence * 100).toFixed(0)}% Match</span>
              </div>
              <p className="text-slate-500 mt-0.5">{res.desc}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
