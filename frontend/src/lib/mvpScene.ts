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
  const geometry = result?.geometry || fallbackVillaGeometry();
  const materials = (geometry.materials || fallbackMaterials).map((m: any) => ({
    ...m,
    id: m.id || m.material_id,
  }));

  return {
    geometry: {
      meshes: geometry.meshes || [],
      rooms: geometry.rooms || [],
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
    { name: "bedroom_1", x: -5, z: 2.9, width: 5, depth: 5, type: "bedroom" },
    { name: "bedroom_2", x: 0, z: 2.9, width: 5, depth: 5, type: "bedroom" },
    { name: "bedroom_3", x: 5, z: 2.9, width: 5, depth: 5, type: "bedroom" },
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
      x: room.x,
      y: room.z,
      width_m: room.width,
      height_m: room.depth,
    })),
    materials: fallbackMaterials,
    style: "modern",
    roof: "flat",
    total_height_m: 3,
  };
}

function mesh(id: string, group: string, position: number[], scale: number[], material_id: string) {
  return { id, component_group: group, type: "box", position, scale, material_id };
}
