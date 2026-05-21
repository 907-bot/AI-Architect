"use client";

import React, { useEffect, useRef, useState } from "react";
import { useStore } from "@/lib/store";
import { Search, MapPin, Loader2 } from "lucide-react";

declare global {
  interface Window {
    L: any;
  }
}

export default function MapPicker() {
  const { plotLat, plotLng, plotWidth, plotDepth, setPlotData } = useStore();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markerInstanceRef = useRef<any>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  // Load Leaflet CDN script and stylesheet
  useEffect(() => {
    if (window.L) {
      setIsLoaded(true);
      return;
    }

    // Leaflet CSS
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
    link.integrity = "sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=";
    link.crossOrigin = "";
    document.head.appendChild(link);

    // Leaflet JS
    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
    script.integrity = "sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=";
    script.crossOrigin = "";
    script.onload = () => {
      setIsLoaded(true);
    };
    document.head.appendChild(script);

    return () => {
      // Clean up tags
      try {
        document.head.removeChild(link);
        document.head.removeChild(script);
      } catch (e) {}
    };
  }, []);

  // Initialize Map
  useEffect(() => {
    if (!isLoaded || !mapContainerRef.current || mapInstanceRef.current) return;

    const L = window.L;

    // Fix default marker icon paths in Leaflet
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
      iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
      shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    });

    // Create Map Instance (Centered on India coordinates originally)
    const map = L.map(mapContainerRef.current, {
      zoomControl: false,
    }).setView([plotLat, plotLng], 12);

    mapInstanceRef.current = map;

    // Dark-themed tiles filter setup (CartoDB Dark Matter tiles look stunning)
    // Light-themed tiles setup (CartoDB Positron tiles look stunning for light minimal theme)
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 20,
    }).addTo(map);

    // Add zoom controls at the bottom right
    L.control.zoom({ position: "bottomright" }).addTo(map);

    // Initial Marker
    const marker = L.marker([plotLat, plotLng], { draggable: true }).addTo(map);
    markerInstanceRef.current = marker;

    // Handle marker drag end to fetch coordinates
    marker.on("dragend", () => {
      const position = marker.getLatLng();
      setPlotData(position.lat, position.lng, plotWidth, plotDepth);
    });

    // Handle Map click to move marker and update coordinates
    map.on("click", (e: any) => {
      const { lat, lng } = e.latlng;
      marker.setLatLng([lat, lng]);
      setPlotData(lat, lng, plotWidth, plotDepth);
    });

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [isLoaded]);

  // Update marker position if coordinates change externally
  useEffect(() => {
    if (mapInstanceRef.current && markerInstanceRef.current) {
      markerInstanceRef.current.setLatLng([plotLat, plotLng]);
      mapInstanceRef.current.panTo([plotLat, plotLng]);
    }
  }, [plotLat, plotLng]);

  // Simple Location Search (Mumbai, Delhi, Chennai, Bangalore etc.)
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || !mapInstanceRef.current) return;

    setIsSearching(true);
    try {
      // Use free OpenStreetMap Nominatim API for geocoding
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          searchQuery
        )}`
      );
      const data = await response.json();
      if (data && data.length > 0) {
        const { lat, lon } = data[0];
        const latitude = parseFloat(lat);
        const longitude = parseFloat(lon);
        
        // Update Store
        setPlotData(latitude, longitude, plotWidth, plotDepth);
        
        // Fly map to selected city
        mapInstanceRef.current.flyTo([latitude, longitude], 14);
      }
    } catch (error) {
      console.error("Geocoding failed", error);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="glass-panel p-4 rounded-xl space-y-3">
      <div className="flex items-center gap-2 text-slate-700">
        <MapPin className="w-4 h-4 text-slate-500" />
        <h3 className="text-xs font-semibold tracking-wide uppercase font-outfit">
          Plot Selector Map
        </h3>
      </div>

      {/* Geocoding Search Bar */}
      <form onSubmit={handleSearch} className="relative flex items-center">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search Indian city or area..."
          className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 pl-3 pr-9 text-xs text-slate-800 placeholder-slate-400 outline-none focus:border-slate-400 transition duration-150"
        />
        <button
          type="submit"
          disabled={isSearching}
          className="absolute right-2 text-slate-400 hover:text-slate-600"
        >
          {isSearching ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
        </button>
      </form>

      {/* Interactive Map Box */}
      <div className="relative h-48 w-full rounded-lg overflow-hidden border border-slate-100 bg-slate-50">
        {!isLoaded ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-400 text-xs">
            <Loader2 className="w-6 h-6 mb-2 animate-spin text-slate-400" />
            Loading satellite map tiles...
          </div>
        ) : (
          <div ref={mapContainerRef} className="h-full w-full z-0" />
        )}
      </div>

      {/* Coordinate Displays */}
      <div className="flex justify-between text-[10px] text-slate-500 font-mono bg-slate-50 p-2 rounded border border-slate-100">
        <div>Lat: {plotLat.toFixed(6)}</div>
        <div>Lng: {plotLng.toFixed(6)}</div>
      </div>
    </div>
  );
}
