"use client";

import React, { useState } from "react";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";
import { useStore } from "@/lib/store";
import axios from "axios";

export default function PromptBar() {
  const [value, setValue] = useState("");
  const projectId = useStore((state) => state.projectId);
  const clientId = useStore((state) => state.clientId);
  const isGenerating = useStore((state) => state.isGenerating);
  
  const setPrompt = useStore((state) => state.setPrompt);
  const setIsGenerating = useStore((state) => state.setIsGenerating);
  const clearAgentLogs = useStore((state) => state.clearAgentLogs);
  const addAgentLog = useStore((state) => state.addAgentLog);
  const updateScene = useStore((state) => state.updateScene);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim() || isGenerating) return;

    setPrompt(value);
    setIsGenerating(true);
    clearAgentLogs();

    // Setup temporary WS listener for logs
    const ws = new WebSocket(`ws://localhost:8000/ws/${clientId}`);
    
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "agent_update") {
          addAgentLog({
            agent: payload.agent,
            message: payload.message,
            data: payload.data
          });

          // Check if it's the complete phase
          if (payload.agent === "evaluation" && payload.message.includes("complete")) {
            // Load resulting scene properties
            const data = payload.data;
            if (data) {
              // Construct geometries
              const geo = data.skeptic?.corrections || data.bear?.enhanced_config || {};
              const geom = {
                meshes: geo.meshes || [
                  { id: "building_base", type: "box", position: [0, 1.5, 0], scale: [8, 3, 10], material_id: "plaster_white" }
                ]
              };
              const conf = {
                drone_path: data.bear?.drone_path || [
                  { index: 0, position: [12, 5, 12], look_at: [0, 1.5, 0], duration_s: 4 },
                  { index: 1, position: [-12, 5, -12], look_at: [0, 1.5, 0], duration_s: 4 }
                ]
              };
              const assets = {
                materials: [
                  { id: "plaster_white", color_hex: "#f4f4f5", roughness: 0.8 },
                  { id: "wood_oak", color_hex: "#b45309", roughness: 0.6 }
                ]
              };
              updateScene(geom, conf, assets);
            }
            setIsGenerating(false);
            ws.close();
          }
        }
      } catch (err) {
        console.error("Error parsing socket message", err);
      }
    };

    try {
      const state = useStore.getState();
      await axios.post("http://localhost:8000/api/agents/generate", {
        prompt: value,
        project_id: projectId,
        client_id: clientId,
        plot_lat: state.plotLat,
        plot_lng: state.plotLng,
        plot_width: state.plotWidth,
        plot_depth: state.plotDepth,
      });
    } catch (err) {
      console.error(err);
      addAgentLog({
        agent: "orchestrator",
        message: "Failed to contact backend API. Falling back to frontend mockup."
      });
      
      // Standalone mock logic to run if the backend API key isn't filled out or server is down
      setTimeout(() => {
        addAgentLog({
          agent: "orchestrator",
          message: "Orchestrator plan ready ✓",
          data: { intent: "modern villa", style: "minimalist" }
        });
        setTimeout(() => {
          addAgentLog({
            agent: "planner",
            message: "Planner: building dimensions 10m x 8m, style Modern Villa"
          });
          setTimeout(() => {
            addAgentLog({
              agent: "layout",
              message: "Layout agent created room floorplan successfully.",
              data: { rooms: [{ id: "lounge", name: "Lounge Area", width_m: 6, height_m: 5 }] }
            });
            setTimeout(() => {
              addAgentLog({
                agent: "geometry",
                message: "Geometry agent generated 3D meshes.",
                data: { meshes: [{ id: "mesh1", type: "box", position: [0, 1.5, 0], scale: [8, 3, 10], material_id: "plaster_white" }] }
              });
              setTimeout(() => {
                addAgentLog({
                  agent: "evaluation",
                  message: "Evaluation complete ✓",
                  data: {
                    bear: {
                      enhanced_config: {
                        meshes: [
                          { id: "base", type: "box", position: [0, 1.5, 0], scale: [8, 3, 10], material_id: "plaster_white" },
                          { id: "roof", type: "box", position: [0, 3.1, 0], scale: [9, 0.2, 11], material_id: "wood_oak" }
                        ]
                      }
                    }
                  }
                });
                
                updateScene(
                  {
                    meshes: [
                      { id: "foundation", component_group: "Foundation", type: "box", position: [0, -0.1, 0], scale: [8, 0.2, 10], material_id: "plaster_white" },
                      { id: "base", component_group: "Walls", type: "box", position: [0, 1.5, 0], scale: [8, 3, 10], material_id: "plaster_white" },
                      { id: "roof", component_group: "Roof", type: "box", position: [0, 3.1, 0], scale: [9, 0.2, 11], material_id: "wood_oak" }
                    ]
                  },
                  {
                    drone_path: [
                      { index: 0, position: [15, 6, 15], look_at: [0, 1.5, 0], duration_s: 4 },
                      { index: 1, position: [-15, 6, -15], look_at: [0, 1.5, 0], duration_s: 4 }
                    ]
                  },
                  {
                    materials: [
                      { id: "plaster_white", color_hex: "#fafafa", roughness: 0.9 },
                      { id: "wood_oak", color_hex: "#8b5a2b", roughness: 0.5 }
                    ]
                  },
                  {
                    compliant: false,
                    issues: [
                      "Ground coverage of 65.0% exceeds NBC suburban threshold of 60.0%.",
                      "Side setback (1.2m) is below the minimum required 1.5m standard."
                    ],
                    actual_far: 2.1,
                    allowed_far: 2.5,
                    actual_coverage_pct: 65,
                    allowed_coverage_pct: 60,
                    vastu_suggestions: [
                      "Main entrance is recommended in the North, East, or North-East corner.",
                      "Kitchen is best placed in the South-East (Agneya) corner."
                    ]
                  }
                );
                setIsGenerating(false);
              }, 1200);
            }, 1000);
          }, 1000);
        }, 1000);
      }, 1000);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full relative">
      <div className="relative flex items-center w-full rounded-2xl bg-white/85 border border-slate-200/60 p-2 pl-4 shadow-xl backdrop-blur-md">
        <Sparkles className="w-5 h-5 text-slate-500 mr-3" />
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={isGenerating}
          placeholder="e.g. A modern two-story glass villa with open courtyard and oak wood ceiling..."
          className="flex-1 bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none pr-4 py-2"
        />
        <button
          type="submit"
          disabled={isGenerating || !value.trim()}
          className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-[#7c93c3] hover:bg-[#8da3d3] text-white font-medium text-xs transition duration-200 shadow-md disabled:opacity-50 disabled:hover:bg-[#7c93c3] disabled:shadow-none"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Building
            </>
          ) : (
            <>
              Generate
              <ArrowRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>
    </form>
  );
}
