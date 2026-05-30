"use client";
import React, { useEffect, useRef, useState, useCallback } from "react";
import { useStore } from "@/lib/store";
import { MapPin, Navigation, Search, Loader2, Eye, Map, RotateCcw } from "lucide-react";

declare global { interface Window { L: any; } }

type MapMode = "satellite" | "street" | "streetview";

export default function MapView() {
  const { plotLat, plotLng, plotWidth, plotDepth, setPlotData } = useStore();
  const mapRef      = useRef<HTMLDivElement>(null);
  const svRef       = useRef<HTMLIFrameElement>(null);
  const mapInst     = useRef<any>(null);
  const marker      = useRef<any>(null);
  const [mode, setMode]       = useState<MapMode>("satellite");
  const [loaded, setLoaded]   = useState(false);
  const [locating, setLocating] = useState(false);
  const [search, setSearch]   = useState("");
  const [searching, setSearching] = useState(false);
  const [svKey, setSvKey]     = useState(0);   // force iframe reload
  const [address, setAddress] = useState<string | null>(null);

  // ── Load Leaflet ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (window.L) { setLoaded(true); return; }
    const css = document.createElement("link");
    css.rel   = "stylesheet";
    css.href  = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    css.crossOrigin = "";
    document.head.appendChild(css);
    const js  = document.createElement("script");
    js.src    = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    js.crossOrigin = "";
    js.onload = () => setLoaded(true);
    document.head.appendChild(js);
  }, []);

  // ── Reverse geocode ─────────────────────────────────────────────────────────
  const reverseGeocode = useCallback(async (lat: number, lng: number) => {
    try {
      const r = await fetch(
        `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`,
        { headers: { "Accept-Language": "en" } }
      );
      const d = await r.json();
      const a = d.address || {};
      setAddress([a.road, a.suburb, a.city || a.town, a.state, a.country]
        .filter(Boolean).slice(0,3).join(", "));
    } catch { setAddress(null); }
  }, []);

  // ── Get user's current location ─────────────────────────────────────────────
  const gotoCurrentLocation = useCallback(() => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const { latitude: lat, longitude: lng } = coords;
        setPlotData(lat, lng, plotWidth, plotDepth);
        reverseGeocode(lat, lng);
        if (mapInst.current) {
          mapInst.current.setView([lat, lng], 18);
          marker.current?.setLatLng([lat, lng]);
        }
        setSvKey(k => k+1);
        setLocating(false);
      },
      () => setLocating(false),
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }, [plotWidth, plotDepth, setPlotData, reverseGeocode]);

  // ── Auto-detect location on first mount ─────────────────────────────────────
  useEffect(() => {
    // Only auto-locate if using default coords (Bombay)
    if (Math.abs(plotLat - 19.076) < 0.001) {
      gotoCurrentLocation();
    } else {
      reverseGeocode(plotLat, plotLng);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Init Leaflet map ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!loaded || !mapRef.current || mapInst.current) return;
    const L = window.L;

    const map = L.map(mapRef.current, { zoomControl: true, attributionControl: false });
    mapInst.current = map;

    // Satellite tile (Esri)
    const satellite = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 21 }
    );
    // Street tile (OSM)
    const street = L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { maxZoom: 19 }
    );

    satellite.addTo(map);
    map.setView([plotLat, plotLng], 18);

    // Marker
    const mk = L.marker([plotLat, plotLng], {
      icon: L.divIcon({
        className: "",
        html: `<div style="background:#7c93c3;width:16px;height:16px;border-radius:50%;border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,0.4)"></div>`,
        iconSize: [16, 16], iconAnchor: [8, 8],
      }),
      draggable: true,
    }).addTo(map);
    marker.current = mk;

    mk.on("dragend", () => {
      const { lat, lng } = mk.getLatLng();
      setPlotData(lat, lng, plotWidth, plotDepth);
      reverseGeocode(lat, lng);
      setSvKey(k => k+1);
    });
    map.on("click", (e: any) => {
      mk.setLatLng(e.latlng);
      setPlotData(e.latlng.lat, e.latlng.lng, plotWidth, plotDepth);
      reverseGeocode(e.latlng.lat, e.latlng.lng);
      setSvKey(k => k+1);
    });

    // Store layer refs for toggle
    (map as any)._satLayer  = satellite;
    (map as any)._streetLayer = street;
  }, [loaded, plotLat, plotLng, plotWidth, plotDepth, setPlotData, reverseGeocode]);

  // ── Toggle satellite / street ────────────────────────────────────────────────
  useEffect(() => {
    const map = mapInst.current;
    if (!map) return;
    const sat = map._satLayer;
    const str = map._streetLayer;
    if (mode === "satellite") { map.addLayer(sat);  map.removeLayer(str); }
    if (mode === "street")    { map.addLayer(str);  map.removeLayer(sat); }
    // "streetview" mode shows the iframe overlay, keep satellite underneath
    if (mode === "streetview") { map.addLayer(sat); map.removeLayer(str); }
  }, [mode]);

  // ── Address search ───────────────────────────────────────────────────────────
  const doSearch = useCallback(async () => {
    if (!search.trim()) return;
    setSearching(true);
    try {
      const r = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(search)}&format=json&limit=1`,
        { headers: { "Accept-Language": "en" } }
      );
      const results = await r.json();
      if (results.length) {
        const { lat, lon, display_name } = results[0];
        const la = parseFloat(lat), ln = parseFloat(lon);
        setPlotData(la, ln, plotWidth, plotDepth);
        setAddress(display_name.split(",").slice(0,3).join(","));
        mapInst.current?.setView([la, ln], 18);
        marker.current?.setLatLng([la, ln]);
        setSvKey(k => k+1);
      }
    } catch { /* noop */ }
    setSearching(false);
  }, [search, plotWidth, plotDepth, setPlotData]);

  // Street View embed URL (works without API key via Google Maps embed)
  const svUrl = `https://www.google.com/maps/embed/v1/streetview?key=AIzaSyD-placeholder&location=${plotLat},${plotLng}&heading=0&pitch=0&fov=80`;
  // Fallback: use the maps embed without API key (place mode shows street view button)
  const mapsEmbedUrl = `https://maps.google.com/maps?q=${plotLat},${plotLng}&z=17&output=embed&layer=s`;

  return (
    <div className="absolute inset-0 flex flex-col bg-[#1a1a2e]">
      {/* ── Header ── */}
      <div className="flex items-center gap-2 px-3 py-2 bg-[#1a1a2e] border-b border-white/10 flex-shrink-0">
        <MapPin className="w-3.5 h-3.5 text-[#7c93c3]" />
        <div className="flex-1 min-w-0">
          <p className="text-[9px] font-bold uppercase tracking-widest text-white/60">Plot Location</p>
          <p className="text-[9px] text-white/40 truncate">
            {address ?? `${plotLat.toFixed(5)}, ${plotLng.toFixed(5)}`}
          </p>
        </div>
        <button onClick={gotoCurrentLocation} disabled={locating}
          className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[#7c93c3]/20 hover:bg-[#7c93c3]/30 text-[9px] font-medium text-[#a0b4d8] transition">
          {locating ? <Loader2 className="w-3 h-3 animate-spin" /> : <Navigation className="w-3 h-3" />}
          {locating ? "Locating…" : "My Location"}
        </button>
      </div>

      {/* ── Search bar ── */}
      <div className="flex gap-2 px-3 py-2 bg-[#1a1a2e] flex-shrink-0">
        <div className="flex-1 flex items-center gap-1.5 bg-white/10 rounded-lg px-2.5 py-1.5">
          <Search className="w-3 h-3 text-white/40 flex-shrink-0" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === "Enter" && doSearch()}
            placeholder="Search address or city…"
            className="flex-1 bg-transparent text-[10px] text-white placeholder-white/30 outline-none" />
        </div>
        <button onClick={doSearch} disabled={searching}
          className="px-3 py-1.5 rounded-lg bg-[#7c93c3] hover:bg-[#8da3d3] text-white text-[9px] font-semibold transition">
          {searching ? <Loader2 className="w-3 h-3 animate-spin" /> : "Go"}
        </button>
      </div>

      {/* ── Mode tabs ── */}
      <div className="flex gap-1 px-3 pb-2 flex-shrink-0">
        {([
          { id:"satellite",  icon:<Map className="w-3 h-3" />,  label:"Satellite"    },
          { id:"street",     icon:<Map className="w-3 h-3" />,  label:"Street Map"   },
          { id:"streetview", icon:<Eye className="w-3 h-3" />,  label:"Street View"  },
        ] as {id:MapMode; icon:React.ReactNode; label:string}[]).map(tab => (
          <button key={tab.id} onClick={() => setMode(tab.id)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[9px] font-semibold transition ${
              mode === tab.id
                ? "bg-[#7c93c3] text-white"
                : "bg-white/10 text-white/50 hover:bg-white/15"
            }`}>
            {tab.icon}{tab.label}
          </button>
        ))}
      </div>

      {/* ── Map / Street View ── */}
      <div className="relative flex-1 min-h-0">
        {/* Leaflet map — always mounted, hidden in streetview mode */}
        <div ref={mapRef}
          className={`absolute inset-0 ${mode === "streetview" ? "opacity-0 pointer-events-none" : "opacity-100"}`}
          style={{ zIndex: 1 }} />

        {/* Street View iframe */}
        {mode === "streetview" && (
          <div className="absolute inset-0 flex flex-col" style={{ zIndex: 2 }}>
            <iframe
              key={svKey}
              ref={svRef}
              className="flex-1 w-full border-0"
              loading="lazy"
              allowFullScreen
              referrerPolicy="no-referrer-when-downgrade"
              src={mapsEmbedUrl}
              title="Google Street View"
            />
            <div className="bg-black/80 px-3 py-1.5 flex items-center justify-between">
              <p className="text-[9px] text-white/50">
                Google Maps Street View · {plotLat.toFixed(5)}, {plotLng.toFixed(5)}
              </p>
              <button onClick={() => setSvKey(k => k+1)}
                className="flex items-center gap-1 text-[9px] text-white/40 hover:text-white/70 transition">
                <RotateCcw className="w-2.5 h-2.5" /> Reload
              </button>
            </div>
          </div>
        )}

        {!loaded && mode !== "streetview" && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#1a1a2e]/80 z-10">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="w-5 h-5 animate-spin text-[#7c93c3]" />
              <p className="text-[10px] text-white/50">Loading map…</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Coordinates bar ── */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#1a1a2e] border-t border-white/10 flex-shrink-0">
        <div className="flex gap-3 text-[9px] font-mono text-white/40">
          <span>Lat {plotLat.toFixed(6)}</span>
          <span>Lng {plotLng.toFixed(6)}</span>
        </div>
        <div className="flex gap-2">
          {[["W",plotWidth,"width"],["D",plotDepth,"depth"]].map(([lbl,val,key]) => (
            <div key={String(key)} className="flex items-center gap-1">
              <span className="text-[8px] text-white/30">{lbl}</span>
              <input type="number" value={Number(val)} min={4} max={200} step={0.5}
                onChange={e => {
                  const n = parseFloat(e.target.value)||Number(val);
                  setPlotData(plotLat, plotLng,
                    key==="width" ? n : plotWidth,
                    key==="depth" ? n : plotDepth);
                }}
                className="w-12 bg-white/10 text-white text-[9px] rounded px-1.5 py-0.5 text-right outline-none focus:bg-white/15" />
              <span className="text-[8px] text-white/30">m</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
