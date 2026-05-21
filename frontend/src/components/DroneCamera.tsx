"use client";

import React from "react";
import { Play, Square, Video, RefreshCw, Compass } from "lucide-react";
import { useStore } from "@/lib/store";

export default function DroneCamera() {
  const isDroneFlying = useStore((state) => state.isDroneFlying);
  const setDroneFlying = useStore((state) => state.setDroneFlying);
  const dronePath = useStore((state) => state.dronePath);
  const currentKeyframe = useStore((state) => state.currentDroneKeyframe);

  const toggleFlight = () => {
    if (!dronePath) return;
    setDroneFlying(!isDroneFlying);
  };

  return (
    <div className="glass-panel p-4 rounded-xl space-y-3">
      <div className="flex items-center gap-2 text-slate-700">
        <Video className="w-4 h-4 text-slate-500" />
        <h3 className="text-xs font-semibold tracking-wide uppercase font-outfit">
          Drone Path Controller
        </h3>
      </div>

      {!dronePath ? (
        <div className="text-slate-400 text-[11px] py-2">
          Generate a structure to initialize autonomous drone flyby path.
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <button
              onClick={toggleFlight}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-medium transition duration-200 ${
                isDroneFlying
                  ? "bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200"
                  : "bg-[#7c93c3] text-white hover:bg-[#8da3d3]"
              }`}
            >
              {isDroneFlying ? (
                <>
                  <Square className="w-3.5 h-3.5 fill-current" />
                  Stop Flight
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  Launch Drone
                </>
              )}
            </button>
          </div>

          <div className="p-2.5 rounded bg-slate-50 border border-slate-100 space-y-1.5">
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>Status</span>
              <span className={isDroneFlying ? "text-emerald-700 font-medium" : "text-slate-400"}>
                {isDroneFlying ? "FLYING" : "DOCKED"}
              </span>
            </div>
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>Keyframes</span>
              <span className="font-mono text-slate-800">
                {currentKeyframe + 1} / {dronePath.length}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
