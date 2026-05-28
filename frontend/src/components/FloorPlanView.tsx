"use client";

import React, { useMemo, useState, useCallback } from "react";
import { 
  DoorOpen, Route, ScanLine, SquareDashedMousePointer, 
  ZoomIn, ZoomOut, Compass, Maximize2, Info,
  Home, UtensilsCrossed, Bed, Bath, DoorOpen2, CircleDot,
  Armchair, Wheat
} from "lucide-react";
import { FloorPlanData } from "@/lib/store";

const ROOM_COLORS: Record<string, string> = {
  living_room: "#dbeafe",
  hallway: "#f1f5f9",
  bedroom: "#ede9fe",
  bathroom: "#cffafe",
  kitchen: "#fef3c7",
  dining_room: "#dcfce7",
  room: "#f8fafc",
};

const ROOM_ICONS: Record<string, React.ReactNode> = {
  living_room: <Home className="w-3 h-3" />,
  hallway: <CircleDot className="w-3 h-3" />,
  bedroom: <Bed className="w-3 h-3" />,
  bathroom: <Bath className="w-3 h-3" />,
  kitchen: <UtensilsCrossed className="w-3 h-3" />,
  dining_room: <Wheat className="w-3 h-3" />,
};

const ROOM_LABELS: Record<string, string> = {
  living_room: "Living Room",
  hallway: "Hallway",
  bedroom: "Bedroom",
  bathroom: "Bathroom",
  kitchen: "Kitchen",
  dining_room: "Dining Room",
};

// Door swing arc helper
function doorSwingArc(cx: number, cy: number, width: number, side: string, scale: number): string {
  const r = width * scale;
  const sweep = side === "front" || side === "right" ? 1 : 0;
  const endX = side === "front" || side === "back" ? r : 0;
  const endY = side === "front" ? -r : (side === "back" ? r : 0);
  
  if (side === "left" || side === "right") {
    return `M ${cx} ${cy} A ${r} ${r} 0 0 ${sweep} ${cx} ${cy + (side === "left" ? -r : r)}`;
  }
  return `M ${cx} ${cy} A ${r} ${r} 0 0 ${sweep} ${cx + (side === "front" ? r : -r)} ${cy}`;
}

export default function FloorPlanView({ floorPlan }: { floorPlan?: FloorPlanData }) {
  const plan = floorPlan || { rooms: [], walls: [], doors: [], windows: [], adjacency: [], circulation: [] };
  const [selectedRoom, setSelectedRoom] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  
  const bounds = useMemo(() => {
    if (!plan.rooms.length) return { minX: -8, maxX: 8, minY: -6, maxY: 6, width: 16, height: 12 };
    const minX = Math.min(...plan.rooms.map((room) => room.x - room.width / 2)) - 1;
    const maxX = Math.max(...plan.rooms.map((room) => room.x + room.width / 2)) + 1;
    const minY = Math.min(...plan.rooms.map((room) => room.y - room.depth / 2)) - 1;
    const maxY = Math.max(...plan.rooms.map((room) => room.y + room.depth / 2)) + 1;
    return { minX, maxX, minY, maxY, width: maxX - minX, height: maxY - minY };
  }, [plan.rooms]);

  const baseScale = 42;
  const scale = baseScale * zoom;
  const pad = 48;
  const width = bounds.width * scale + pad * 2;
  const height = bounds.height * scale + pad * 2;
  const toX = useCallback((x: number) => (x - bounds.minX) * scale + pad, [bounds.minX, scale]);
  const toY = useCallback((y: number) => height - ((y - bounds.minY) * scale + pad), [bounds.minY, height, scale]);
  const toLen = useCallback((value: number) => value * scale, [scale]);
  
  const selectedRoomData = plan.rooms.find(r => r.id === selectedRoom);
  const adjacentRooms = useMemo(() => {
    if (!selectedRoom) return [];
    return plan.adjacency
      .filter(adj => adj.from === selectedRoom || adj.to === selectedRoom)
      .map(adj => adj.from === selectedRoom ? adj.to : adj.from);
  }, [selectedRoom, plan.adjacency]);

  return (
    <div className="absolute inset-0 bg-[#f8fafc] overflow-auto">
      <div className="min-w-full min-h-full p-6 flex flex-col gap-4">
        {/* Header with controls */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wide text-slate-800">Architectural Floor Plan</h2>
            <p className="text-[11px] text-slate-500">Top-down view with room labels, dimensions & circulation paths</p>
          </div>
          <div className="flex items-center gap-2">
            {/* Zoom controls */}
            <div className="flex items-center gap-1 rounded border border-slate-200 bg-white">
              <button 
                onClick={() => setZoom(z => Math.max(0.5, z - 0.25))}
                className="p-1.5 hover:bg-slate-100 transition"
                title="Zoom out"
              >
                <ZoomOut className="h-3.5 w-3.5 text-slate-600" />
              </button>
              <span className="px-2 text-[10px] font-mono text-slate-500">{Math.round(zoom * 100)}%</span>
              <button 
                onClick={() => setZoom(z => Math.min(2, z + 0.25))}
                className="p-1.5 hover:bg-slate-100 transition"
                title="Zoom in"
              >
                <ZoomIn className="h-3.5 w-3.5 text-slate-600" />
              </button>
            </div>
            
            {/* Legend */}
            <div className="flex items-center gap-2 text-[10px] text-slate-600">
              <span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-1">
                <div className="w-2 h-2 rounded bg-[#a16207]" />Doors
              </span>
              <span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-1">
                <div className="w-4 h-0.5 bg-[#0284c7] rounded" />Windows
              </span>
              <span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-1">
                <div className="w-4 border-t border-dashed border-[#2563eb]" />Circulation
              </span>
            </div>
          </div>
        </div>

        <div className="flex flex-1 gap-4">
          {/* Main SVG canvas */}
          <div className="flex-1 overflow-auto rounded border border-slate-200 bg-white shadow-sm relative">
            <svg 
              width={width} 
              height={height} 
              viewBox={`0 0 ${width} ${height}`} 
              className="min-w-full cursor-crosshair"
              style={{ maxHeight: "calc(100vh - 280px)" }}
            >
              <defs>
                {/* Grid pattern */}
                <pattern id="grid" width={scale} height={scale} patternUnits="userSpaceOnUse">
                  <path d={`M ${scale} 0 L 0 0 0 ${scale}`} fill="none" stroke="#e2e8f0" strokeWidth="0.5" />
                </pattern>
                {/* Shadow filter for rooms */}
                <filter id="roomShadow" x="-20%" y="-20%" width="140%" height="140%">
                  <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.1" />
                </filter>
                {/* Glow filter for selected room */}
                <filter id="selectedGlow">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              
              {/* Background with grid */}
              <rect x="0" y="0" width={width} height={height} fill="url(#grid)" />
              
              {/* Compass Rose */}
              <g transform={`translate(${width - 60}, 40)`}>
                <circle cx="25" cy="25" r="24" fill="white" stroke="#e2e8f0" strokeWidth="1.5" />
                <polygon points="25,5 28,25 25,20 22,25" fill="#334155" />
                <polygon points="25,45 28,25 25,30 22,25" fill="#cbd5e1" />
                <polygon points="5,25 25,22 20,25 25,28" fill="#cbd5e1" />
                <polygon points="45,25 25,22 30,25 25,28" fill="#cbd5e1" />
                <text x="25" y="10" textAnchor="middle" className="text-[9px] font-bold fill-slate-700">N</text>
                <text x="25" y="47" textAnchor="middle" className="text-[9px] fill-slate-500">S</text>
                <text x="8" y="28" textAnchor="middle" className="text-[9px] fill-slate-500">W</text>
                <text x="42" y="28" textAnchor="middle" className="text-[9px] fill-slate-500">E</text>
              </g>
              
              {/* Wall thickness visualization */}
              {plan.walls.map((wall) => {
                const isSelected = selectedRoom ? plan.rooms.find(r => r.id === wall.room)?.id === selectedRoom : false;
                return (
                  <line
                    key={wall.id}
                    x1={toX(wall.x1)}
                    y1={toY(wall.y1)}
                    x2={toX(wall.x2)}
                    y2={toY(wall.y2)}
                    stroke={isSelected ? "#7c93c3" : "#475569"}
                    strokeWidth={toLen(wall.thickness) * 1.5}
                    strokeLinecap="round"
                    opacity={isSelected ? 1 : 0.85}
                  />
                );
              })}
              
              {/* Room fill areas */}
              {plan.rooms.map((room) => {
                const isSelected = room.id === selectedRoom;
                const isAdjacent = adjacentRooms.includes(room.id);
                return (
                  <g key={room.id} onClick={() => setSelectedRoom(isSelected ? null : room.id)} style={{ cursor: "pointer" }}>
                    <rect
                      x={toX(room.x - room.width / 2)}
                      y={toY(room.y + room.depth / 2)}
                      width={toLen(room.width)}
                      height={toLen(room.depth)}
                      fill={isSelected ? "#7c93c3/30" : (isAdjacent ? "#7c93c3/15" : ROOM_COLORS[room.type] || ROOM_COLORS.room)}
                      stroke={isSelected ? "#7c93c3" : (isAdjacent ? "#93c5fd" : "#334155")}
                      strokeWidth={isSelected ? 3 : 2}
                      strokeDasharray={isSelected ? "none" : "none"}
                      filter={isSelected ? "url(#selectedGlow)" : undefined}
                      rx="2"
                    />
                  </g>
                );
              })}

              {/* Room labels with type icon */}
              {plan.rooms.map((room) => {
                const isSelected = room.id === selectedRoom;
                const icon = ROOM_ICONS[room.type];
                return (
                  <g key={`label-${room.id}`}>
                    {/* Room type icon badge */}
                    <g transform={`translate(${toX(room.x) - 8}, ${toY(room.y + room.depth/2) + 12})`}>
                      <rect 
                        x="0" y="0" 
                        width="16" height="16" 
                        rx="4" 
                        fill={isSelected ? "#7c93c3" : "#475569"}
                        opacity="0.9"
                      />
                      <g transform="translate(4, 4)">
                        <foreignObject width="8" height="8">
                          <div className="text-white">
                            {icon}
                          </div>
                        </foreignObject>
                      </g>
                    </g>
                    
                    {/* Room name label */}
                    <text 
                      x={toX(room.x)} 
                      y={toY(room.y) - 4}
                      textAnchor="middle" 
                      className={`text-[11px] font-bold ${isSelected ? "fill-slate-800" : "fill-slate-700"}`}
                    >
                      {ROOM_LABELS[room.type] || room.name.replaceAll("_", " ")}
                    </text>
                    
                    {/* Dimensions */}
                    <text 
                      x={toX(room.x)} 
                      y={toY(room.y) + 14}
                      textAnchor="middle" 
                      className="fill-slate-500 text-[9px] font-mono"
                    >
                      {room.width.toFixed(1)}m × {room.depth.toFixed(1)}m
                    </text>
                    
                    {/* Area */}
                    <text 
                      x={toX(room.x)} 
                      y={toY(room.y) + 26}
                      textAnchor="middle" 
                      className="fill-slate-400 text-[8px]"
                    >
                      {room.area_m2 || Math.round(room.width * room.depth)} m²
                    </text>
                  </g>
                );
              })}

              {/* Circulation paths */}
              {plan.circulation.map((path, index) => {
                const points = path.points.map((point) => `${toX(point.x)},${toY(point.y)}`).join(" ");
                return (
                  <g key={`circ-${path.from}-${path.to}-${index}`}>
                    <polyline 
                      points={points} 
                      fill="none" 
                      stroke="#2563eb" 
                      strokeWidth="2.5" 
                      strokeDasharray="8 4"
                      opacity="0.7" 
                    />
                    {/* Arrow heads */}
                    {path.points.slice(1).map((pt, i) => (
                      <circle
                        key={i}
                        cx={toX(pt.x)}
                        cy={toY(pt.y)}
                        r="3"
                        fill="#2563eb"
                        opacity="0.7"
                      />
                    ))}
                  </g>
                );
              })}

              {/* Adjacency connections */}
              {plan.adjacency.map((adj, index) => {
                const fromRoom = plan.rooms.find(r => r.id === adj.from);
                const toRoom = plan.rooms.find(r => r.id === adj.to);
                if (!fromRoom || !toRoom) return null;
                return (
                  <line
                    key={`adj-${index}`}
                    x1={toX(fromRoom.x)}
                    y1={toY(fromRoom.y)}
                    x2={toX(toRoom.x)}
                    y2={toY(toRoom.y)}
                    stroke="#94a3b8"
                    strokeWidth="1"
                    strokeDasharray="4 4"
                    opacity="0.5"
                  />
                );
              })}

              {/* Windows */}
              {plan.windows.map((window) => (
                <g key={window.id}>
                  <line
                    x1={toX(window.x - window.width / 2)}
                    y1={toY(window.y)}
                    x2={toX(window.x + window.width / 2)}
                    y2={toY(window.y)}
                    stroke="#0284c7"
                    strokeWidth="6"
                    strokeLinecap="round"
                  />
                  <line
                    x1={toX(window.x - window.width / 2)}
                    y1={toY(window.y)}
                    x2={toX(window.x + window.width / 2)}
                    y2={toY(window.y)}
                    stroke="#7dd3fc"
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </g>
              ))}

              {/* Doors with swing arc */}
              {plan.doors.map((door) => {
                const doorColor = "#a16207";
                return (
                  <g key={door.id}>
                    {/* Door opening */}
                    <rect
                      x={toX(door.x) - toLen(door.width) / 2}
                      y={toY(door.y) - toLen(0.08)}
                      width={toLen(door.width)}
                      height={toLen(0.08)}
                      fill="white"
                      stroke={doorColor}
                      strokeWidth="1"
                    />
                    {/* Door panel */}
                    <rect
                      x={toX(door.x) - toLen(door.width) / 2 + 1}
                      y={toY(door.y) - toLen(0.04)}
                      width={toLen(door.width) - 2}
                      height={toLen(0.04)}
                      fill={doorColor}
                      opacity="0.9"
                      rx="1"
                    />
                    {/* Door swing arc */}
                    <path
                      d={doorSwingArc(toX(door.x), toY(door.y), door.width, door.side, scale)}
                      fill="none"
                      stroke={doorColor}
                      strokeWidth="1.5"
                      opacity="0.6"
                    />
                  </g>
                );
              })}
              
              {/* Dimension lines */}
              {plan.rooms.map((room) => {
                const isSelected = room.id === selectedRoom;
                if (!isSelected) return null;
                return (
                  <g key={`dims-${room.id}`} className="opacity-60">
                    {/* Width dimension */}
                    <line
                      x1={toX(room.x - room.width / 2)}
                      y1={toY(room.y - room.depth / 2) - 8}
                      x2={toX(room.x + room.width / 2)}
                      y2={toY(room.y - room.depth / 2) - 8}
                      stroke="#334155"
                      strokeWidth="0.5"
                    />
                    <line
                      x1={toX(room.x - room.width / 2)}
                      y1={toY(room.y - room.depth / 2) - 12}
                      x2={toX(room.x - room.width / 2)}
                      y2={toY(room.y - room.depth / 2) - 4}
                      stroke="#334155"
                      strokeWidth="0.5"
                    />
                    <line
                      x1={toX(room.x + room.width / 2)}
                      y1={toY(room.y - room.depth / 2) - 12}
                      x2={toX(room.x + room.width / 2)}
                      y2={toY(room.y - room.depth / 2) - 4}
                      stroke="#334155"
                      strokeWidth="0.5"
                    />
                    
                    {/* Depth dimension */}
                    <line
                      x1={toX(room.x + room.width / 2) + 8}
                      y1={toY(room.y - room.depth / 2)}
                      x2={toX(room.x + room.width / 2) + 8}
                      y2={toY(room.y + room.depth / 2)}
                      stroke="#334155"
                      strokeWidth="0.5"
                    />
                    <line
                      x1={toX(room.x + room.width / 2) + 4}
                      y1={toY(room.y - room.depth / 2)}
                      x2={toX(room.x + room.width / 2) + 12}
                      y2={toY(room.y - room.depth / 2)}
                      stroke="#334155"
                      strokeWidth="0.5"
                    />
                    <line
                      x1={toX(room.x + room.width / 2) + 4}
                      y1={toY(room.y + room.depth / 2)}
                      x2={toX(room.x + room.width / 2) + 12}
                      y2={toY(room.y + room.depth / 2)}
                      stroke="#334155"
                      strokeWidth="0.5"
                    />
                  </g>
                );
              })}
            </svg>
            
            {/* Empty state */}
            {!plan.rooms.length && (
              <div className="absolute inset-0 flex items-center justify-center text-slate-400">
                <div className="flex items-center gap-2 text-sm">
                  <SquareDashedMousePointer className="h-4 w-4" />
                  Generate a scene to see the floor plan.
                </div>
              </div>
            )}
          </div>
          
          {/* Room info panel */}
          {selectedRoomData && (
            <div className="w-64 flex flex-col gap-3">
              {/* Selected room details */}
              <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    selectedRoomData.type === 'living_room' ? 'bg-blue-100 text-blue-600' :
                    selectedRoomData.type === 'bedroom' ? 'bg-purple-100 text-purple-600' :
                    selectedRoomData.type === 'bathroom' ? 'bg-cyan-100 text-cyan-600' :
                    selectedRoomData.type === 'kitchen' ? 'bg-amber-100 text-amber-600' :
                    selectedRoomData.type === 'dining_room' ? 'bg-green-100 text-green-600' :
                    'bg-slate-100 text-slate-600'
                  }`}>
                    {ROOM_ICONS[selectedRoomData.type] || <Info className="w-4 h-4" />}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-800">
                      {ROOM_LABELS[selectedRoomData.type] || selectedRoomData.name}
                    </h3>
                    <p className="text-[10px] text-slate-500 capitalize">{selectedRoomData.type?.replace('_', ' ')}</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <div className="bg-slate-50 rounded p-2">
                    <div className="text-[9px] text-slate-500 uppercase">Width</div>
                    <div className="text-sm font-mono font-semibold">{selectedRoomData.width.toFixed(1)}m</div>
                  </div>
                  <div className="bg-slate-50 rounded p-2">
                    <div className="text-[9px] text-slate-500 uppercase">Depth</div>
                    <div className="text-sm font-mono font-semibold">{selectedRoomData.depth.toFixed(1)}m</div>
                  </div>
                </div>
                
                <div className="bg-slate-50 rounded p-2 mb-3">
                  <div className="text-[9px] text-slate-500 uppercase">Area</div>
                  <div className="text-lg font-mono font-semibold text-slate-700">
                    {selectedRoomData.area_m2 || Math.round(selectedRoomData.width * selectedRoomData.depth)} m²
                  </div>
                </div>
                
                <div className="text-[10px] text-slate-500">
                  Position: ({selectedRoomData.x.toFixed(1)}, {selectedRoomData.y.toFixed(1)})
                </div>
              </div>
              
              {/* Adjacent rooms */}
              {adjacentRooms.length > 0 && (
                <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
                  <h4 className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-2 flex items-center gap-1.5">
                    <Route className="w-3 h-3" /> Connected Rooms
                  </h4>
                  <div className="space-y-1.5">
                    {adjacentRooms.map(adjId => {
                      const adjRoom = plan.rooms.find(r => r.id === adjId);
                      if (!adjRoom) return null;
                      return (
                        <div 
                          key={adjId}
                          className="flex items-center gap-2 p-2 bg-slate-50 rounded cursor-pointer hover:bg-slate-100 transition"
                          onClick={() => setSelectedRoom(adjId)}
                        >
                          <div className={`w-6 h-6 rounded flex items-center justify-center ${
                            adjRoom.type === 'living_room' ? 'bg-blue-100' :
                            adjRoom.type === 'bedroom' ? 'bg-purple-100' :
                            adjRoom.type === 'bathroom' ? 'bg-cyan-100' :
                            adjRoom.type === 'kitchen' ? 'bg-amber-100' :
                            'bg-slate-100'
                          }`}>
                            {ROOM_ICONS[adjRoom.type]}
                          </div>
                          <span className="text-xs font-medium text-slate-700">
                            {ROOM_LABELS[adjRoom.type] || adjRoom.name}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              
              {/* Door info */}
              {plan.doors.filter(d => d.room_a === selectedRoom || d.room_b === selectedRoom).length > 0 && (
                <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
                  <h4 className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-2 flex items-center gap-1.5">
                    <DoorOpen2 className="w-3 h-3" /> Doors
                  </h4>
                  <div className="space-y-1.5">
                    {plan.doors
                      .filter(d => d.room_a === selectedRoom || d.room_b === selectedRoom)
                      .map(door => {
                        const otherRoom = door.room_a === selectedRoom ? door.room_b : door.room_a;
                        return (
                          <div key={door.id} className="flex items-center gap-2 p-2 bg-slate-50 rounded">
                            <DoorOpen className="w-3 h-3 text-amber-600" />
                            <span className="text-[10px] text-slate-600">
                              → {plan.rooms.find(r => r.id === otherRoom)?.name || otherRoom}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}
              
              {/* Window info */}
              {plan.windows.filter(w => plan.rooms.find(r => r.id === selectedRoom)?.name === w.room).length > 0 && (
                <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4">
                  <h4 className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-2 flex items-center gap-1.5">
                    <ScanLine className="w-3 h-3" /> Windows
                  </h4>
                  <div className="space-y-1.5">
                    {plan.windows
                      .filter(w => w.room === selectedRoom || plan.rooms.find(r => r.id === selectedRoom)?.name === w.room)
                      .map(window => (
                        <div key={window.id} className="flex items-center gap-2 p-2 bg-slate-50 rounded">
                          <div className="w-6 h-0.5 bg-sky-500 rounded" />
                          <span className="text-[10px] text-slate-600">
                            {window.width}m · {window.side}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
