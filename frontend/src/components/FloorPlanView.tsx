"use client";

import React, { useMemo } from "react";
import { DoorOpen, Route, ScanLine, SquareDashedMousePointer } from "lucide-react";
import { FloorPlanData } from "@/lib/store";

const ROOM_COLORS: Record<string, string> = {
  living_room: "#dbeafe",
  hallway: "#f8fafc",
  bedroom: "#ede9fe",
  bathroom: "#cffafe",
  kitchen: "#fef3c7",
  dining_room: "#dcfce7",
  room: "#f1f5f9",
};

export default function FloorPlanView({ floorPlan }: { floorPlan?: FloorPlanData }) {
  const plan = floorPlan || { rooms: [], walls: [], doors: [], windows: [], adjacency: [], circulation: [] };
  const bounds = useMemo(() => {
    if (!plan.rooms.length) return { minX: -8, maxX: 8, minY: -6, maxY: 6, width: 16, height: 12 };
    const minX = Math.min(...plan.rooms.map((room) => room.x - room.width / 2)) - 1;
    const maxX = Math.max(...plan.rooms.map((room) => room.x + room.width / 2)) + 1;
    const minY = Math.min(...plan.rooms.map((room) => room.y - room.depth / 2)) - 1;
    const maxY = Math.max(...plan.rooms.map((room) => room.y + room.depth / 2)) + 1;
    return { minX, maxX, minY, maxY, width: maxX - minX, height: maxY - minY };
  }, [plan.rooms]);

  const scale = 42;
  const pad = 32;
  const width = bounds.width * scale + pad * 2;
  const height = bounds.height * scale + pad * 2;
  const toX = (x: number) => (x - bounds.minX) * scale + pad;
  const toY = (y: number) => height - ((y - bounds.minY) * scale + pad);
  const toLen = (value: number) => value * scale;

  return (
    <div className="absolute inset-0 bg-[#f8fafc] overflow-auto">
      <div className="min-w-full min-h-full p-6 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-800">Architectural Plan</h2>
            <p className="text-[11px] text-slate-500">Same SceneGraph as the Blender model: rooms, walls, openings, adjacency, circulation.</p>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-slate-600">
            <span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-1"><DoorOpen className="h-3 w-3" />Doors</span>
            <span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-1"><ScanLine className="h-3 w-3" />Windows</span>
            <span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-1"><Route className="h-3 w-3" />Circulation</span>
          </div>
        </div>

        <div className="flex-1 overflow-auto rounded border border-slate-200 bg-white shadow-sm">
          <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="min-w-full">
            <defs>
              <pattern id="grid" width={scale} height={scale} patternUnits="userSpaceOnUse">
                <path d={`M ${scale} 0 L 0 0 0 ${scale}`} fill="none" stroke="#e2e8f0" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect x="0" y="0" width={width} height={height} fill="url(#grid)" />

            {plan.rooms.map((room) => {
              const x = toX(room.x - room.width / 2);
              const y = toY(room.y + room.depth / 2);
              return (
                <g key={room.id}>
                  <rect
                    x={x}
                    y={y}
                    width={toLen(room.width)}
                    height={toLen(room.depth)}
                    fill={ROOM_COLORS[room.type] || ROOM_COLORS.room}
                    stroke="#334155"
                    strokeWidth="2"
                  />
                  <text x={toX(room.x)} y={toY(room.y) - 6} textAnchor="middle" className="fill-slate-800 text-[11px] font-bold">
                    {room.name.replaceAll("_", " ")}
                  </text>
                  <text x={toX(room.x)} y={toY(room.y) + 10} textAnchor="middle" className="fill-slate-500 text-[9px]">
                    {room.width}m x {room.depth}m · {room.area_m2 || Math.round(room.width * room.depth)} m2
                  </text>
                </g>
              );
            })}

            {plan.circulation.map((path, index) => {
              const points = path.points.map((point) => `${toX(point.x)},${toY(point.y)}`).join(" ");
              return <polyline key={`${path.from}-${path.to}-${index}`} points={points} fill="none" stroke="#2563eb" strokeWidth="2" strokeDasharray="6 6" opacity="0.75" />;
            })}

            {plan.doors.map((door) => (
              <g key={door.id}>
                <circle cx={toX(door.x)} cy={toY(door.y)} r="5" fill="#a16207" stroke="#fff" strokeWidth="2" />
                <path d={`M ${toX(door.x)} ${toY(door.y)} a ${toLen(door.width)} ${toLen(door.width)} 0 0 1 ${toLen(door.width)} ${door.side === "front" ? -toLen(door.width) : toLen(door.width)}`} fill="none" stroke="#a16207" strokeWidth="1.5" opacity="0.7" />
              </g>
            ))}

            {plan.windows.map((window) => (
              <line
                key={window.id}
                x1={toX(window.x - window.width / 2)}
                y1={toY(window.y)}
                x2={toX(window.x + window.width / 2)}
                y2={toY(window.y)}
                stroke="#0284c7"
                strokeWidth="5"
                strokeLinecap="round"
              />
            ))}
          </svg>
        </div>

        {!plan.rooms.length && (
          <div className="absolute inset-0 flex items-center justify-center text-slate-400">
            <div className="flex items-center gap-2 text-sm"><SquareDashedMousePointer className="h-4 w-4" />Generate a scene to see the floor plan.</div>
          </div>
        )}
      </div>
    </div>
  );
}
