import { create } from "zustand";

export interface AgentUpdate { agent: string; message: string; data?: any; }
export interface ChatMessage {
  id: string; role: "user" | "assistant"; content: string; isStreaming?: boolean;
  buildingSummary?: { type?: string; floors?: number; features?: string[]; compliant?: boolean; far?: number; coverage?: number; };
}
export interface Room { id: string; name: string; type?: string; x: number; y: number; width_m: number; height_m: number; depth_m?: number; area_m2?: number; }
export interface FloorPlanRoom { id: string; name: string; type: string; x: number; y: number; width: number; depth: number; area_m2?: number; floor?: number; }
export interface FloorPlanWall { id: string; room: string; x1: number; y1: number; x2: number; y2: number; thickness: number; floor?: number; }
export interface FloorPlanOpening { id: string; room?: string; room_a?: string; room_b?: string; x: number; y: number; width: number; side: string; floor?: number; }
export interface CirculationPath { from: string; to: string; points: { x: number; y: number }[]; floor?: number; }
export interface FloorPlanData {
  rooms: FloorPlanRoom[]; walls: FloorPlanWall[]; doors: FloorPlanOpening[];
  windows: FloorPlanOpening[]; adjacency: { from: string; to: string }[];
  circulation: CirculationPath[]; total_floors?: number;
}
export interface Mesh { id: string; component_group: string; type: string; position: [number,number,number]; scale: [number,number,number]; rotation?: [number,number,number]; material_id: string; }
export interface GeometryData { meshes?: Mesh[]; rooms?: Room[]; floor_plan?: FloorPlanData; adjacency?: { from: string; to: string }[]; circulation?: CirculationPath[]; style?: string; total_height_m?: number; }
export interface CameraConfig { type: string; fov: number; position: [number,number,number]; target: [number,number,number]; }
export interface Keyframe { index: number; position: [number,number,number]; look_at: [number,number,number]; duration_s: number; }
export interface SceneConfig { camera?: CameraConfig; lighting?: any[]; drone_path?: Keyframe[]; }
export interface AssetManifest { materials?: any[]; furniture?: any[]; }
export interface ComplianceData {
  compliant: boolean; issues: string[]; actual_far?: number; allowed_far?: number;
  actual_coverage_pct?: number; allowed_coverage_pct?: number;
  vastu_suggestions?: string[]; seismic_guideline?: string;
}
export interface PlacedAsset {
  placement_id: string; asset_uid: string; position: [number,number,number];
  rotation: [number,number,number]; scale: number;
  glb_url?: string; local_path?: string; name?: string; thumbnail?: string;
}
export type ProjectionType = "perspective_1p"|"perspective_2p"|"perspective_3p"|"orthographic_top"|"orthographic_front"|"orthographic_side"|"isometric"|"oblique_cavalier"|"oblique_cabinet";
export type ComponentGroupFilter = "All"|"Floor Slabs"|"Walls"|"Interior"|"Foundation"|"Structure"|"Exterior"|"Windows"|"Doors"|"Roof"|"Entrance"|"Pool"|"Landscape"|"Boundary"|"Chimney"|"Garage";

interface ArchitectStore {
  projectId: string; clientId: string; currentPrompt: string; isGenerating: boolean;
  agentLogs: AgentUpdate[]; chatMessages: ChatMessage[];
  geometryData: GeometryData | null; sceneConfig: SceneConfig | null;
  assetManifest: AssetManifest | null; generatedGlbPath: string | null;
  latestToon: string | null; dronePath: Keyframe[] | null;
  isDroneFlying: boolean; currentDroneKeyframe: number;
  plotLat: number; plotLng: number; plotWidth: number; plotDepth: number;
  activeProjection: ProjectionType; visibleComponentGroup: ComponentGroupFilter;
  complianceData: ComplianceData | null;
  placedAssets: PlacedAsset[]; selectedAssetUid: string | null; isAssetPaletteOpen: boolean;
  // NEW
  selectedRoomId: string | null;
  isWalkthrough: boolean;
  activeFloor: number;

  setProjectId: (id: string) => void; setPrompt: (p: string) => void;
  setIsGenerating: (g: boolean) => void; addAgentLog: (l: AgentUpdate) => void;
  clearAgentLogs: () => void;
  updateScene: (g: GeometryData, c: SceneConfig, a: AssetManifest, compliance?: ComplianceData) => void;
  setGeneratedGlbPath: (p: string | null) => void; setLatestToon: (t: string | null) => void;
  addChatMessage: (m: Omit<ChatMessage,"id">) => string;
  updateChatMessage: (id: string, u: Partial<ChatMessage>) => void;
  setDroneFlying: (f: boolean) => void; setDroneKeyframe: (i: number) => void;
  setPlotData: (lat: number, lng: number, w: number, d: number) => void;
  setActiveProjection: (p: ProjectionType) => void;
  setVisibleComponentGroup: (g: ComponentGroupFilter) => void;
  setComplianceData: (d: ComplianceData | null) => void;
  addPlacedAsset: (a: PlacedAsset) => void; removePlacedAsset: (id: string) => void;
  updatePlacedAsset: (id: string, u: Partial<PlacedAsset>) => void;
  setSelectedAssetUid: (id: string | null) => void;
  setAssetPaletteOpen: (o: boolean) => void; clearPlacedAssets: () => void;
  // NEW actions
  setSelectedRoomId: (id: string | null) => void;
  setWalkthrough: (on: boolean) => void;
  setActiveFloor: (floor: number) => void;
}

export const useStore = create<ArchitectStore>((set) => ({
  projectId: "default-project",
  clientId: typeof window !== "undefined" ? Math.random().toString(36).substring(7) : "server",
  currentPrompt: "", isGenerating: false, agentLogs: [],
  chatMessages: [{ id: "welcome", role: "assistant", content: "Describe a house and I will compile it through the local TOON pipeline." }],
  geometryData: null, sceneConfig: null, assetManifest: null,
  generatedGlbPath: null, latestToon: null, dronePath: null,
  isDroneFlying: false, currentDroneKeyframe: 0,
  plotLat: 19.076, plotLng: 72.8777, plotWidth: 20.0, plotDepth: 30.0,
  activeProjection: "perspective_2p", visibleComponentGroup: "All",
  complianceData: null, placedAssets: [], selectedAssetUid: null, isAssetPaletteOpen: false,
  // NEW defaults
  selectedRoomId: null, isWalkthrough: false, activeFloor: 0,

  setProjectId: (id) => set({ projectId: id }),
  setPrompt: (p) => set({ currentPrompt: p }),
  setIsGenerating: (g) => set({ isGenerating: g }),
  addAgentLog: (l) => set((s) => ({ agentLogs: [...s.agentLogs, l] })),
  clearAgentLogs: () => set({ agentLogs: [] }),
  updateScene: (geometry, config, assets, compliance) => set({
    geometryData: geometry, sceneConfig: config, assetManifest: assets,
    dronePath: config?.drone_path || null, complianceData: compliance || null
  }),
  setGeneratedGlbPath: (p) => set({ generatedGlbPath: p }),
  setLatestToon: (t) => set({ latestToon: t }),
  addChatMessage: (message) => {
    const id = `${message.role}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    set((s) => ({ chatMessages: [...s.chatMessages, { ...message, id }] }));
    return id;
  },
  updateChatMessage: (id, updates) => set((s) => ({
    chatMessages: s.chatMessages.map((m) => m.id === id ? { ...m, ...updates } : m)
  })),
  setDroneFlying: (f) => set({ isDroneFlying: f }),
  setDroneKeyframe: (i) => set({ currentDroneKeyframe: i }),
  setPlotData: (lat, lng, w, d) => set({ plotLat: lat, plotLng: lng, plotWidth: w, plotDepth: d }),
  setActiveProjection: (p) => set({ activeProjection: p }),
  setVisibleComponentGroup: (g) => set({ visibleComponentGroup: g }),
  setComplianceData: (d) => set({ complianceData: d }),
  addPlacedAsset: (a) => set((s) => ({ placedAssets: [...s.placedAssets, a] })),
  removePlacedAsset: (id) => set((s) => ({ placedAssets: s.placedAssets.filter((a) => a.placement_id !== id) })),
  updatePlacedAsset: (id, u) => set((s) => ({ placedAssets: s.placedAssets.map((a) => a.placement_id === id ? { ...a, ...u } : a) })),
  setSelectedAssetUid: (id) => set({ selectedAssetUid: id }),
  setAssetPaletteOpen: (o) => set({ isAssetPaletteOpen: o }),
  clearPlacedAssets: () => set({ placedAssets: [] }),
  // NEW
  setSelectedRoomId: (id) => set({ selectedRoomId: id }),
  setWalkthrough: (on) => set({ isWalkthrough: on }),
  setActiveFloor: (floor) => set({ activeFloor: floor }),
}));
