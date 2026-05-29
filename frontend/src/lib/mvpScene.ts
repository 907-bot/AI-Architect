import { AssetManifest, ComplianceData, GeometryData, SceneConfig } from "@/lib/store";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const DEFAULT_MVP_PROMPT = "Modern 3 bedroom villa with flat roof";

const fallbackMaterials = [
  { id: "floor_concrete", color_hex: "#b8bec8", roughness: 0.9 },
  { id: "wall_plaster", color_hex: "#eef1f4", roughness: 0.82 },
  { id: "roof_dark", color_hex: "#4b5563", roughness: 0.75, opacity: 0.72, transparent: true },
  { id: "glass_clear", color_hex: "#bfe7ff", roughness: 0.08, transmission: 0.7, opacity: 0.42, transparent: true },
  { id: "wood_warm", color_hex: "#a16207", roughness: 0.7 },
  { id: "fabric_blue", color_hex: "#4068a8", roughness: 0.9 },
];

export function normalizeMvpResponse(raw: any): {
  geometry: GeometryData;
  sceneConfig: SceneConfig;
  assets: AssetManifest;
  compliance: ComplianceData | null;
  toon: string | null;
  glbPath: string | null;
} {
  const result = raw?.data || raw;
  
  // Don't use fallback - return empty if no geometry
  if (!result?.geometry) {
    return {
      geometry: { meshes: [], rooms: [], style: "modern" },
      sceneConfig: { drone_path: [] },
      assets: { materials: [] },
      compliance: null,
      toon: result?.toon || null,
      glbPath: result?.glb_path || null,
    };
  }
  
  const geometry = result.geometry;
  const materials = (geometry.materials || fallbackMaterials).map((m: any) => ({
    ...m,
    id: m.id || m.material_id,
  }));

  return {
    geometry: {
      meshes: geometry.meshes || [],
      rooms: geometry.rooms || [],
      floor_plan: geometry.floor_plan,
      adjacency: geometry.adjacency || geometry.floor_plan?.adjacency || [],
      circulation: geometry.circulation || geometry.floor_plan?.circulation || [],
      style: geometry.style || "modern",
      total_height_m: geometry.total_height_m || 3,
    },
    sceneConfig: {
      drone_path: [
        { index: 0, position: [18, 8, 18], look_at: [0, 2, 0], duration_s: 4 },
        { index: 1, position: [-18, 8, -18], look_at: [0, 2, 0], duration_s: 4 },
      ],
    },
    assets: { materials },
    compliance: result?.compliance || null,
    toon: result?.toon || null,
    glbPath: result?.glb_path || null,
  };
}

export function fallbackVillaGeometry(): any {
  const rooms = [
    { name: "living_room", x: 0, z: -3, width: 8, depth: 6, type: "living_room" },
    { name: "hallway", x: 0, z: 1.25, width: 2, depth: 3.5, type: "hallway" },
    { name: "bedroom_1", x: -5, z: 2.9, width: 5, depth: 5, type: "bedroom" },
    { name: "bedroom_2", x: 0, z: 2.9, width: 5, depth: 5, type: "bedroom" },
    { name: "bedroom_3", x: 5, z: 2.9, width: 5, depth: 5, type: "bedroom" },
    { name: "bathroom_1", x: -9, z: 2.9, width: 3, depth: 3, type: "bathroom" },
    { name: "kitchen", x: 7, z: -3, width: 4, depth: 4, type: "kitchen" },
    { name: "dining_room", x: 7, z: 1.6, width: 5, depth: 4, type: "dining_room" },
  ];
  const meshes: any[] = [
    mesh("foundation", "Foundation", [0, -0.15, 0], [16, 0.3, 11.5], "floor_concrete"),
  ];

  rooms.forEach((room, index) => {
    const prefix = `room_${index}_${room.name}`;
    meshes.push(mesh(`${prefix}_floor`, "Floor Slabs", [room.x, 0.03, room.z], [room.width, 0.06, room.depth], "floor_concrete"));
    meshes.push(mesh(`${prefix}_wall_front`, "Walls", [room.x, 1.5, room.z + room.depth / 2], [room.width, 3, 0.18], "wall_plaster"));
    meshes.push(mesh(`${prefix}_wall_back`, "Walls", [room.x, 1.5, room.z - room.depth / 2], [room.width, 3, 0.18], "wall_plaster"));
    meshes.push(mesh(`${prefix}_wall_left`, "Walls", [room.x - room.width / 2, 1.5, room.z], [0.18, 3, room.depth], "wall_plaster"));
    meshes.push(mesh(`${prefix}_wall_right`, "Walls", [room.x + room.width / 2, 1.5, room.z], [0.18, 3, room.depth], "wall_plaster"));
    meshes.push(mesh(`${prefix}_window_front`, "Windows", [room.x, 1.75, room.z + room.depth / 2 + 0.02], [2.2, 1, 0.05], "glass_clear"));
    meshes.push(mesh(`${prefix}_window_back`, "Windows", [room.x, 1.75, room.z - room.depth / 2 - 0.02], [2.2, 1, 0.05], "glass_clear"));
    meshes.push(
      room.type === "living_room"
        ? mesh(`${prefix}_sofa`, "Interior", [room.x, 0.45, room.z], [2.4, 0.8, 0.9], "fabric_blue")
        : mesh(`${prefix}_bed`, "Interior", [room.x, 0.32, room.z], [2, 0.55, 1.6], "fabric_blue")
    );
  });

  meshes.push(mesh("roof", "Roof", [0, 3.2, 0], [16.2, 0.4, 11.7], "roof_dark"));

  return {
    meshes,
    rooms: rooms.map((room) => ({
      id: room.name,
      name: room.name,
      type: room.type,
      x: room.x,
      y: room.z,
      width_m: room.width,
      height_m: room.depth,
      depth_m: room.depth,
      area_m2: Math.round(room.width * room.depth),
    })),
    floor_plan: fallbackFloorPlan(rooms),
    adjacency: [
      { from: "living_room", to: "hallway" },
      { from: "living_room", to: "kitchen" },
      { from: "kitchen", to: "dining_room" },
      { from: "hallway", to: "bedroom_1" },
      { from: "hallway", to: "bedroom_2" },
      { from: "hallway", to: "bedroom_3" },
      { from: "hallway", to: "bathroom_1" },
    ],
    materials: fallbackMaterials,
    style: "modern",
    roof: "flat",
    total_height_m: 3,
  };
}

function mesh(id: string, group: string, position: number[], scale: number[], material_id: string) {
  return { id, component_group: group, type: "box", position, scale, material_id };
}

function fallbackFloorPlan(rooms: any[]) {
  const adjacency = [
    { from: "living_room", to: "hallway" },
    { from: "living_room", to: "kitchen" },
    { from: "kitchen", to: "dining_room" },
    { from: "hallway", to: "bedroom_1" },
    { from: "hallway", to: "bedroom_2" },
    { from: "hallway", to: "bedroom_3" },
    { from: "hallway", to: "bathroom_1" },
  ];
  const byName = Object.fromEntries(rooms.map((room) => [room.name, room]));
  return {
    rooms: rooms.map((room) => ({
      id: room.name,
      name: room.name,
      type: room.type,
      x: room.x,
      y: room.z,
      width: room.width,
      depth: room.depth,
      area_m2: Math.round(room.width * room.depth),
    })),
    walls: rooms.flatMap((room) => [
      { id: `${room.name}_north`, room: room.name, x1: room.x - room.width / 2, y1: room.z + room.depth / 2, x2: room.x + room.width / 2, y2: room.z + room.depth / 2, thickness: 0.18 },
      { id: `${room.name}_south`, room: room.name, x1: room.x - room.width / 2, y1: room.z - room.depth / 2, x2: room.x + room.width / 2, y2: room.z - room.depth / 2, thickness: 0.18 },
      { id: `${room.name}_west`, room: room.name, x1: room.x - room.width / 2, y1: room.z - room.depth / 2, x2: room.x - room.width / 2, y2: room.z + room.depth / 2, thickness: 0.18 },
      { id: `${room.name}_east`, room: room.name, x1: room.x + room.width / 2, y1: room.z - room.depth / 2, x2: room.x + room.width / 2, y2: room.z + room.depth / 2, thickness: 0.18 },
    ]),
    doors: adjacency.map((edge, index) => {
      const from = byName[edge.from];
      const to = byName[edge.to];
      return { id: `door_${index}`, room_a: edge.from, room_b: edge.to, x: (from.x + to.x) / 2, y: (from.z + to.z) / 2, width: 0.9, side: "back" };
    }),
    windows: rooms.map((room) => ({ id: `${room.name}_window`, room: room.name, x: room.x, y: room.z + room.depth / 2, width: Math.min(2.4, room.width * 0.4), side: "back" })),
    adjacency,
    circulation: adjacency.map((edge) => {
      const from = byName[edge.from];
      const to = byName[edge.to];
      return { from: edge.from, to: edge.to, points: [{ x: from.x, y: from.z }, { x: to.x, y: to.z }] };
    }),
  };
}
