"use client";

import React, { useMemo } from "react";
import { Compass, Ruler, Maximize2 } from "lucide-react";
import { FloorPlanData } from "@/lib/store";

// Professional architectural colors
const ROOM_COLORS: Record<string, string> = {
  living_room: "#e8f4f8",
  hallway: "#f5f5f5",
  bedroom: "#fff8e7",
  bathroom: "#e0f7fa",
  kitchen: "#fff3e0",
  dining_room: "#e8f5e9",
  garage: "#eceff1",
  study: "#f3e5f5",
  room: "#fafafa",
};

const ROOM_LABELS: Record<string, string> = {
  living_room: "Living Room",
  hallway: "Hallway",
  bedroom: "Bedroom",
  bathroom: "Bathroom",
  kitchen: "Kitchen",
  dining_room: "Dining Room",
  garage: "Garage",
  study: "Study",
  room: "Room",
};

export default function FloorPlanView({ floorPlan }: { floorPlan?: FloorPlanData }) {
  const plan = floorPlan || { 
    rooms: [], 
    walls: [], 
    doors: [], 
    windows: [], 
    adjacency: [], 
    circulation: [] 
  };
  
  const bounds = useMemo(() => {
    if (!plan.rooms.length) return { minX: -10, maxX: 10, minY: -8, maxY: 8, width: 20, height: 16 };
    const minX = Math.min(...plan.rooms.map((room) => room.x - room.width / 2)) - 1;
    const maxX = Math.max(...plan.rooms.map((room) => room.x + room.width / 2)) + 1;
    const minY = Math.min(...plan.rooms.map((room) => room.y - room.depth / 2)) - 1;
    const maxY = Math.max(...plan.rooms.map((room) => room.y + room.depth / 2)) + 1;
    return { minX, maxX, minY, maxY, width: maxX - minX, height: maxY - minY };
  }, [plan.rooms]);

  const scale = 36;
  const padding = 80;
  const headerHeight = 60;
  const footerHeight = 50;
  const width = Math.max(bounds.width * scale + padding * 2, 600);
  const height = bounds.height * scale + padding * 2 + headerHeight + footerHeight;
  const toX = (x: number) => (x - bounds.minX) * scale + padding;
  const toY = (y: number) => headerHeight + (bounds.maxY - y) * scale + padding;
  const toLen = (value: number) => value * scale;

  return (
    <div className="absolute inset-0 bg-white overflow-auto">
      <div className="min-w-full min-h-full">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white border-b border-slate-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold uppercase tracking-wider text-slate-800 flex items-center gap-2">
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M3 9h18M9 21V9" />
                </svg>
                Floor Plan
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">Architectural Layout • Ground Floor</p>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-600">
              <div className="flex items-center gap-1.5">
                <Compass className="w-4 h-4 text-slate-400" />
                <span className="font-medium">N</span>
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2L8 8l4 2 4-2-4-6z" />
                </svg>
              </div>
              <div className="flex items-center gap-1.5">
                <Ruler className="w-4 h-4 text-slate-400" />
                <span>1:50</span>
              </div>
            </div>
          </div>
        </div>

        {/* Floor Plan SVG */}
        <div className="p-4">
          <svg 
            width={width} 
            height={height - headerHeight - footerHeight} 
            viewBox={`0 0 ${width} ${height - headerHeight - footerHeight}`} 
            className="w-full"
            style={{ maxWidth: '100%', height: 'auto' }}
          >
            <defs>
              {/* Grid pattern */}
              <pattern id="fp-grid" width={scale} height={scale} patternUnits="userSpaceOnUse">
                <path d={`M ${scale} 0 L 0 0 0 ${scale}`} fill="none" stroke="#f0f0f0" strokeWidth="0.5" />
              </pattern>
              
              {/* Wall pattern */}
              <pattern id="wall-pattern" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="2" height="4" fill="#d4d4d4" />
              </pattern>
              
              {/* Door symbol */}
              <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                <path d="M0,0 L0,6 L9,3 z" fill="#8b5a2b" />
              </marker>
            </defs>

            {/* Background with grid */}
            <rect x="0" y="0" width={width} height={height - headerHeight - footerHeight} fill="#fafafa" />
            <rect x="40" y="20" width={width - 80} height={height - headerHeight - footerHeight - 60} fill="url(#fp-grid)" />
            
            {/* Outer boundary */}
            <rect 
              x={toX(bounds.minX)} 
              y={toY(bounds.maxY)} 
              width={toLen(bounds.width)} 
              height={toLen(bounds.height)} 
              fill="none" 
              stroke="#1e293b" 
              strokeWidth="3" 
            />

            {/* Rooms */}
            {plan.rooms.map((room, idx) => {
              const roomLabel = ROOM_LABELS[room.type] || room.name?.replace(/_/g, " ") || "Room";
              const x = toX(room.x - room.width / 2);
              const y = toY(room.y + room.depth / 2);
              const roomW = toLen(room.width);
              const roomH = toLen(room.depth);
              const area = room.area_m2 || Math.round(room.width * room.depth);
              
              return (
                <g key={room.id || idx} className="group">
                  {/* Room fill */}
                  <rect
                    x={x}
                    y={y}
                    width={roomW}
                    height={roomH}
                    fill={ROOM_COLORS[room.type] || ROOM_COLORS.room}
                    stroke="#64748b"
                    strokeWidth="1.5"
                    rx="2"
                  />
                  
                  {/* Room name label */}
                  <text 
                    x={toX(room.x)} 
                    y={toY(room.y) - 8}
                    textAnchor="middle" 
                    className="fill-slate-800 text-[14px] font-bold"
                    style={{ fontFamily: 'system-ui, sans-serif', textTransform: 'uppercase', letterSpacing: '0.05em' }}
                  >
                    {roomLabel}
                  </text>
                  
                  {/* Dimensions */}
                  <text 
                    x={toX(room.x)} 
                    y={toY(room.y) + (roomH > roomW ? -roomH/2 + 15 : 15)} 
                    textAnchor="middle" 
                    className="fill-slate-500 text-[10px] font-mono"
                  >
                    {room.width}m × {room.depth}m
                  </text>
                  
                  {/* Area */}
                  <text 
                    x={toX(room.x)} 
                    y={toY(room.y) + (roomH > roomW ? -roomH/2 + 30 : 30)} 
                    textAnchor="middle" 
                    className="fill-slate-400 text-[11px]"
                  >
                    {area} sq.ft
                  </text>
                </g>
              );
            })}

            {/* Walls (if provided separately) */}
            {plan.walls.map((wall, idx) => (
              <g key={`wall-${idx}`}>
                <line
                  x1={toX(wall.x1)}
                  y1={toY(wall.y1)}
                  x2={toX(wall.x2)}
                  y2={toY(wall.y2)}
                  stroke="#1e293b"
                  strokeWidth="8"
                  strokeLinecap="round"
                />
                <line
                  x1={toX(wall.x1)}
                  y1={toY(wall.y1)}
                  x2={toX(wall.x2)}
                  y2={toY(wall.y2)}
                  stroke="#475569"
                  strokeWidth="6"
                  strokeLinecap="round"
                />
              </g>
            ))}

            {/* Doors */}
            {plan.doors.map((door, idx) => {
              const doorAngle = door.rotation || 0;
              return (
                <g key={`door-${idx}`} transform={`translate(${toX(door.x)}, ${toY(door.y)}) rotate(${doorAngle})`}>
                  {/* Door opening */}
                  <circle cx="0" cy="0" r="3" fill="#1e293b" />
                  {/* Door swing arc */}
                  <path
                    d={`M 0 0 A ${toLen(door.width || 0.9)} ${toLen(door.width || 0.9)} 0 0 1 ${toLen(door.width || 0.9)} ${-toLen(door.width || 0.9) * 0.3}`}
                    fill="none"
                    stroke="#8b5a2b"
                    strokeWidth="2"
                    strokeDasharray="none"
                  />
                  {/* Door panel */}
                  <line
                    x1="0"
                    y1="0"
                    x2={toLen(door.width || 0.9)}
                    y2="0"
                    stroke="#1e293b"
                    strokeWidth="3"
                  />
                </g>
              );
            })}

            {/* Windows */}
            {plan.windows.map((window, idx) => (
              <g key={`window-${idx}`}>
                <line
                  x1={toX(window.x - (window.width || 1) / 2)}
                  y1={toY(window.y)}
                  x2={toX(window.x + (window.width || 1) / 2)}
                  y2={toY(window.y)}
                  stroke="#0ea5e9"
                  strokeWidth="8"
                  strokeLinecap="butt"
                />
                <line
                  x1={toX(window.x - (window.width || 1) / 2)}
                  y1={toY(window.y)}
                  x2={toX(window.x + (window.width || 1) / 2)}
                  y2={toY(window.y)}
                  stroke="#ffffff"
                  strokeWidth="4"
                  strokeLinecap="butt"
                  strokeDasharray="2 2"
                />
              </g>
            ))}

            {/* Circulation paths */}
            {plan.circulation.map((path, idx) => {
              const points = path.points.map((p) => `${toX(p.x)},${toY(p.y)}`).join(" ");
              return (
                <polyline
                  key={`circ-${idx}`}
                  points={points}
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="2"
                  strokeDasharray="8 4"
                  opacity="0.6"
                  markerEnd="url(#arrow)"
                />
              );
            })}

            {/* Dimension lines */}
            {plan.rooms.length > 0 && (
              <>
                {/* Bottom dimension */}
                <line x1={toX(bounds.minX)} y1={toY(bounds.minY) + 25} x2={toX(bounds.maxX)} y2={toY(bounds.minY) + 25} stroke="#94a3b8" strokeWidth="1" />
                <line x1={toX(bounds.minX)} y1={toY(bounds.minY) + 20} x2={toX(bounds.minX)} y2={toY(bounds.minY) + 30} stroke="#94a3b8" strokeWidth="1" />
                <line x1={toX(bounds.maxX)} y1={toY(bounds.minY) + 20} x2={toX(bounds.maxX)} y2={toY(bounds.minY) + 30} stroke="#94a3b8" strokeWidth="1" />
                <text x={(toX(bounds.minX) + toX(bounds.maxX)) / 2} y={toY(bounds.minY) + 40} textAnchor="middle" className="fill-slate-600 text-[10px] font-mono">
                  {Math.round(bounds.width)} m
                </text>
                
                {/* Left dimension */}
                <line x1={toX(bounds.minX) - 25} y1={toY(bounds.minY)} x2={toX(bounds.minX) - 25} y2={toY(bounds.maxY)} stroke="#94a3b8" strokeWidth="1" />
                <line x1={toX(bounds.minX) - 20} y1={toY(bounds.minY)} x2={toX(bounds.minX) - 30} y2={toY(bounds.minY)} stroke="#94a3b8" strokeWidth="1" />
                <line x1={toX(bounds.minX) - 20} y1={toY(bounds.maxY)} x2={toX(bounds.minX) - 30} y2={toY(bounds.maxY)} stroke="#94a3b8" strokeWidth="1" />
              </>
            )}
          </svg>
        </div>

        {/* Footer with legend */}
        <div className="sticky bottom-0 z-10 bg-white border-t border-slate-200 px-6 py-3">
          <div className="flex items-center justify-between text-[10px] text-slate-500">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm bg-[#e8f4f8] border border-slate-300" />
                <span>Living</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm bg-[#fff8e7] border border-slate-300" />
                <span>Bedroom</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm bg-[#e0f7fa] border border-slate-300" />
                <span>Bathroom</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm bg-[#fff3e0] border border-slate-300" />
                <span>Kitchen</span>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <div className="w-6 h-0.5 bg-slate-400" />
                <span>Wall (6")</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-4 h-0.5 bg-blue-500" />
                <span>Window</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-4 h-0.5 bg-amber-700" />
                <span>Door</span>
              </div>
            </div>
          </div>
        </div>

        {/* Empty state */}
        {!plan.rooms.length && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/90">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center">
                <Maximize2 className="w-8 h-8 text-slate-400" />
              </div>
              <p className="text-sm text-slate-500">Generate a house to see the floor plan</p>
              <p className="text-xs text-slate-400 mt-1">The floor plan will show room layouts, dimensions, and circulation paths</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
