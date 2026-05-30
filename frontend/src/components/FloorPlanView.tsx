"use client";
import React, { useMemo, useState, useRef, useCallback } from "react";
import { Compass, Ruler, Download, FileText, Layers } from "lucide-react";
import { FloorPlanData } from "@/lib/store";
import { useStore } from "@/lib/store";

const ROOM_COLORS: Record<string, string> = {
  living_room: "#e8f4f8", hallway: "#f5f5f5", bedroom: "#fff8e7",
  bathroom: "#e0f7fa", kitchen: "#fff3e0", dining_room: "#e8f5e9",
  garage: "#eceff1", study: "#f3e5f5", room: "#fafafa", office: "#fce4ec",
};
const ROOM_LABELS: Record<string, string> = {
  living_room: "Living Room", hallway: "Hallway", bedroom: "Bedroom",
  bathroom: "Bathroom", kitchen: "Kitchen", dining_room: "Dining Room",
  garage: "Garage", study: "Study", room: "Room", office: "Office",
};

export default function FloorPlanView({ floorPlan }: { floorPlan?: FloorPlanData }) {
  const plan = floorPlan || { rooms: [], walls: [], doors: [], windows: [], adjacency: [], circulation: [] };
  const selectedRoomId  = useStore((s) => s.selectedRoomId);
  const setSelectedRoom = useStore((s) => s.setSelectedRoomId);
  const activeFloor     = useStore((s) => s.activeFloor);
  const setActiveFloor  = useStore((s) => s.setActiveFloor);
  const svgRef = useRef<SVGSVGElement>(null);

  // Determine total floors
  const totalFloors = useMemo(() => {
    const maxFloor = Math.max(0, ...plan.rooms.map((r) => r.floor ?? 0));
    return plan.total_floors ?? maxFloor + 1;
  }, [plan]);

  // Filter by active floor
  const visibleRooms   = useMemo(() => plan.rooms.filter((r) => (r.floor ?? 0) === activeFloor), [plan.rooms, activeFloor]);
  const visibleWalls   = useMemo(() => plan.walls.filter((w) => (w.floor ?? 0) === activeFloor), [plan.walls, activeFloor]);
  const visibleDoors   = useMemo(() => plan.doors.filter((d) => (d.floor ?? 0) === activeFloor), [plan.doors, activeFloor]);
  const visibleWindows = useMemo(() => plan.windows.filter((w) => (w.floor ?? 0) === activeFloor), [plan.windows, activeFloor]);

  const rooms = visibleRooms.length > 0 ? visibleRooms : plan.rooms;

  const bounds = useMemo(() => {
    if (!rooms.length) return { minX: -10, maxX: 10, minY: -8, maxY: 8, width: 20, height: 16 };
    const minX = Math.min(...rooms.map((r) => r.x - r.width / 2)) - 1;
    const maxX = Math.max(...rooms.map((r) => r.x + r.width / 2)) + 1;
    const minY = Math.min(...rooms.map((r) => r.y - r.depth / 2)) - 1;
    const maxY = Math.max(...rooms.map((r) => r.y + r.depth / 2)) + 1;
    return { minX, maxX, minY, maxY, width: maxX - minX, height: maxY - minY };
  }, [rooms]);

  const scale  = 36;
  const pad    = 80;
  const svgW   = Math.max(bounds.width * scale + pad * 2, 600);
  const svgH   = bounds.height * scale + pad * 2;
  const toX    = (x: number) => (x - bounds.minX) * scale + pad;
  const toY    = (y: number) => (bounds.maxY - y) * scale + pad;
  const toLen  = (v: number) => v * scale;

  // ── PNG Export ──────────────────────────────────────────────────────────────
  const exportPNG = useCallback(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const xml   = new XMLSerializer().serializeToString(svg);
    const blob  = new Blob([xml], { type: "image/svg+xml" });
    const url   = URL.createObjectURL(blob);
    const img   = new Image();
    img.onload  = () => {
      const canvas = document.createElement("canvas");
      canvas.width  = svgW * 2;
      canvas.height = svgH * 2;
      const ctx = canvas.getContext("2d")!;
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      const a = document.createElement("a");
      a.href     = canvas.toDataURL("image/png");
      a.download = `floor-plan-level-${activeFloor + 1}.png`;
      a.click();
    };
    img.src = url;
  }, [svgW, svgH, activeFloor]);

  // ── PDF Export (print dialog) ───────────────────────────────────────────────
  const exportPDF = useCallback(() => {
    const svg  = svgRef.current;
    if (!svg) return;
    const xml  = new XMLSerializer().serializeToString(svg);
    const b64  = btoa(unescape(encodeURIComponent(xml)));
    const win  = window.open("", "_blank")!;
    win.document.write(`
      <!DOCTYPE html><html><head><title>Floor Plan — Level ${activeFloor + 1}</title>
      <style>
        @media print { body { margin: 0; } }
        body { font-family: system-ui; background: #fff; }
        h2  { font-size: 14px; text-transform: uppercase; letter-spacing: 0.08em; color: #1e293b; margin: 16px 24px 4px; }
        p   { font-size: 10px; color: #64748b; margin: 0 24px 12px; }
        img { width: 100%; max-width: 900px; display: block; margin: 0 auto; }
        .meta { font-size: 9px; color: #94a3b8; text-align: center; margin: 8px; }
      </style></head><body>
      <h2>AI Architect — Floor Plan</h2>
      <p>Level ${activeFloor + 1} of ${totalFloors} · Scale 1:50 · ${rooms.length} room${rooms.length !== 1 ? "s" : ""}</p>
      <img src="data:image/svg+xml;base64,${b64}" />
      <p class="meta">Generated by AI Architect · ${new Date().toLocaleDateString()}</p>
      <script>window.onload=()=>{ window.print(); }<\/script>
      </body></html>`);
    win.document.close();
  }, [activeFloor, totalFloors, rooms.length]);

  return (
    <div className="absolute inset-0 bg-white overflow-auto flex flex-col">

      {/* ── Header ── */}
      <div className="sticky top-0 z-10 bg-white border-b border-slate-200 px-5 py-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 21V9" />
            </svg>
            Floor Plan
          </h2>
          <p className="text-[10px] text-slate-400 mt-0.5">Architectural Layout · Level {activeFloor + 1}</p>
        </div>

        {/* Floor selector */}
        {totalFloors > 1 && (
          <div className="flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <div className="flex gap-1">
              {Array.from({ length: totalFloors }, (_, i) => (
                <button key={i} onClick={() => setActiveFloor(i)}
                  className={`w-7 h-7 rounded-lg text-[10px] font-bold transition-all ${
                    activeFloor === i
                      ? "bg-[#7c93c3] text-white shadow-sm"
                      : "bg-slate-100 text-slate-500 hover:bg-slate-200"
                  }`}>
                  {i + 1}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
            <Compass className="w-3.5 h-3.5 text-slate-400" /><span>N ↑</span>
            <Ruler className="w-3.5 h-3.5 text-slate-400 ml-2" /><span>1:50</span>
          </div>
          <button onClick={exportPNG}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-[10px] font-medium text-slate-600 transition">
            <Download className="w-3 h-3" /> PNG
          </button>
          <button onClick={exportPDF}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#7c93c3]/15 hover:bg-[#7c93c3]/25 text-[10px] font-medium text-[#5a73a3] transition">
            <FileText className="w-3 h-3" /> PDF
          </button>
        </div>
      </div>

      {/* ── SVG Plan ── */}
      <div className="flex-1 p-4 overflow-auto">
        <svg ref={svgRef} width={svgW} height={svgH}
          viewBox={`0 0 ${svgW} ${svgH}`}
          className="w-full" style={{ maxWidth: "100%", height: "auto" }}
          xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="fp-grid" width={scale} height={scale} patternUnits="userSpaceOnUse">
              <path d={`M ${scale} 0 L 0 0 0 ${scale}`} fill="none" stroke="#f0f0f0" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width={svgW} height={svgH} fill="#fafafa" />
          <rect x={40} y={20} width={svgW - 80} height={svgH - 40} fill="url(#fp-grid)" />
          <rect x={toX(bounds.minX)} y={toY(bounds.maxY)}
            width={toLen(bounds.width)} height={toLen(bounds.height)}
            fill="none" stroke="#1e293b" strokeWidth="3" />

          {/* Rooms */}
          {rooms.map((room, idx) => {
            const label   = ROOM_LABELS[room.type] || (room.name || "Room").replace(/_/g, " ");
            const rx      = toX(room.x - room.width / 2);
            const ry      = toY(room.y + room.depth / 2);
            const rw      = toLen(room.width);
            const rh      = toLen(room.depth);
            const isSelected = selectedRoomId === (room.id || `${idx}`);
            return (
              <g key={room.id || idx} style={{ cursor: "pointer" }}
                onClick={() => setSelectedRoom(isSelected ? null : (room.id || `${idx}`))}>
                <rect x={rx} y={ry} width={rw} height={rh}
                  fill={isSelected ? "#fef3c7" : (ROOM_COLORS[room.type] || "#fafafa")}
                  stroke={isSelected ? "#f59e0b" : "#64748b"}
                  strokeWidth={isSelected ? 2.5 : 1.5} rx="2" />
                {isSelected && (
                  <rect x={rx-1} y={ry-1} width={rw+2} height={rh+2}
                    fill="none" stroke="#f59e0b" strokeWidth="1" strokeDasharray="4 2" rx="3" />
                )}
                <text x={toX(room.x)} y={toY(room.y) - 6} textAnchor="middle"
                  style={{ fontFamily: "system-ui,sans-serif", fontSize: 11, fontWeight: 700,
                    fill: "#1e293b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {label}
                </text>
                <text x={toX(room.x)} y={toY(room.y) + 10} textAnchor="middle"
                  style={{ fontFamily: "monospace", fontSize: 9, fill: "#64748b" }}>
                  {room.width}×{room.depth}m
                </text>
                {room.area_m2 && (
                  <text x={toX(room.x)} y={toY(room.y) + 22} textAnchor="middle"
                    style={{ fontFamily: "monospace", fontSize: 8, fill: "#94a3b8" }}>
                    {room.area_m2} m²
                  </text>
                )}
              </g>
            );
          })}

          {/* Walls */}
          {(visibleWalls.length > 0 ? visibleWalls : plan.walls).map((w, i) => (
            <g key={`w-${i}`}>
              <line x1={toX(w.x1)} y1={toY(w.y1)} x2={toX(w.x2)} y2={toY(w.y2)}
                stroke="#1e293b" strokeWidth="8" strokeLinecap="round" />
              <line x1={toX(w.x1)} y1={toY(w.y1)} x2={toX(w.x2)} y2={toY(w.y2)}
                stroke="#475569" strokeWidth="5" strokeLinecap="round" />
            </g>
          ))}

          {/* Doors */}
          {(visibleDoors.length > 0 ? visibleDoors : plan.doors).map((d, i) => (
            <g key={`d-${i}`} transform={`translate(${toX(d.x)},${toY(d.y)}) rotate(${d.side === "south" ? 0 : d.side === "east" ? -90 : d.side === "west" ? 90 : 180})`}>
              <path d={`M 0 0 A ${toLen(d.width||0.9)} ${toLen(d.width||0.9)} 0 0 1 ${toLen(d.width||0.9)} 0`}
                fill="none" stroke="#b45309" strokeWidth="1.5" />
              <line x1="0" y1="0" x2={toLen(d.width||0.9)} y2="0" stroke="#1e293b" strokeWidth="3" />
              <circle cx="0" cy="0" r="2.5" fill="#1e293b" />
            </g>
          ))}

          {/* Windows */}
          {(visibleWindows.length > 0 ? visibleWindows : plan.windows).map((w, i) => (
            <g key={`win-${i}`}>
              <line x1={toX(w.x-(w.width||1)/2)} y1={toY(w.y)} x2={toX(w.x+(w.width||1)/2)} y2={toY(w.y)}
                stroke="#0ea5e9" strokeWidth="8" strokeLinecap="butt" />
              <line x1={toX(w.x-(w.width||1)/2)} y1={toY(w.y)} x2={toX(w.x+(w.width||1)/2)} y2={toY(w.y)}
                stroke="#fff" strokeWidth="4" strokeDasharray="2 2" />
            </g>
          ))}

          {/* Circulation */}
          {plan.circulation.filter((p) => !p.floor || p.floor === activeFloor).map((p, i) => {
            const pts = p.points.map((pt) => `${toX(pt.x)},${toY(pt.y)}`).join(" ");
            return (
              <polyline key={`c-${i}`} points={pts} fill="none"
                stroke="#3b82f6" strokeWidth="1.5" strokeDasharray="6 3" opacity="0.5" />
            );
          })}

          {/* Dimension lines */}
          {rooms.length > 0 && (
            <>
              <line x1={toX(bounds.minX)} y1={toY(bounds.minY)+28} x2={toX(bounds.maxX)} y2={toY(bounds.minY)+28} stroke="#94a3b8" strokeWidth="1" />
              <line x1={toX(bounds.minX)} y1={toY(bounds.minY)+22} x2={toX(bounds.minX)} y2={toY(bounds.minY)+34} stroke="#94a3b8" strokeWidth="1" />
              <line x1={toX(bounds.maxX)} y1={toY(bounds.minY)+22} x2={toX(bounds.maxX)} y2={toY(bounds.minY)+34} stroke="#94a3b8" strokeWidth="1" />
              <text x={(toX(bounds.minX)+toX(bounds.maxX))/2} y={toY(bounds.minY)+44}
                textAnchor="middle" style={{ fontFamily:"monospace", fontSize:9, fill:"#64748b" }}>
                {Math.round(bounds.width)} m
              </text>
              <line x1={toX(bounds.minX)-28} y1={toY(bounds.minY)} x2={toX(bounds.minX)-28} y2={toY(bounds.maxY)} stroke="#94a3b8" strokeWidth="1" />
              <text x={toX(bounds.minX)-38} y={(toY(bounds.minY)+toY(bounds.maxY))/2}
                textAnchor="middle" transform={`rotate(-90,${toX(bounds.minX)-38},${(toY(bounds.minY)+toY(bounds.maxY))/2})`}
                style={{ fontFamily:"monospace", fontSize:9, fill:"#64748b" }}>
                {Math.round(bounds.height)} m
              </text>
            </>
          )}
        </svg>
      </div>

      {/* ── Footer legend ── */}
      <div className="sticky bottom-0 z-10 bg-white border-t border-slate-200 px-5 py-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2 text-[9px] text-slate-500">
          <div className="flex items-center gap-3 flex-wrap">
            {Object.entries(ROOM_COLORS).slice(0,4).map(([k,c]) => (
              <div key={k} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-sm border border-slate-200" style={{ background: c }} />
                <span>{ROOM_LABELS[k]}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1"><div className="w-5 h-0.5 bg-slate-600" /><span>Wall</span></div>
            <div className="flex items-center gap-1"><div className="w-4 h-0.5 bg-sky-500" /><span>Window</span></div>
            <div className="flex items-center gap-1"><div className="w-4 h-0.5 bg-amber-700" /><span>Door</span></div>
            {selectedRoomId && (
              <button onClick={() => setSelectedRoom(null)}
                className="ml-2 px-2 py-0.5 rounded bg-amber-100 text-amber-700 font-medium text-[9px]">
                Clear selection ×
              </button>
            )}
          </div>
        </div>
      </div>

      {!plan.rooms.length && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/90">
          <div className="text-center">
            <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-slate-100 flex items-center justify-center">
              <Layers className="w-7 h-7 text-slate-400" />
            </div>
            <p className="text-sm text-slate-500">Generate a building to see the floor plan</p>
            <p className="text-xs text-slate-400 mt-1">Supports multi-floor navigation and PDF/PNG export</p>
          </div>
        </div>
      )}
    </div>
  );
}
