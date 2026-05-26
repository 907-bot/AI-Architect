import { create } from "zustand";

export interface AgentUpdate {
  agent: string;
  message: string;
  data?: any;
}

export interface Room {
  id: string;
  name: string;
  x: number;
  y: number;
  width_m: number;
  height_m: number;
}

export interface Mesh {
  id: string;
  component_group: string;
  type: string;
  position: [number, number, number];
  scale: [number, number, number];
  rotation?: [number, number, number];
  material_id: string;
}

export interface GeometryData {
  meshes?: Mesh[];
  rooms?: Room[];
  style?: string;
  total_height_m?: number;
}

export interface CameraConfig {
  type: string;
  fov: number;
  position: [number, number, number];
  target: [number, number, number];
}

export interface Keyframe {
  index: number;
  position: [number, number, number];
  look_at: [number, number, number];
  duration_s: number;
}

export interface SceneConfig {
  camera?: CameraConfig;
  lighting?: any[];
  drone_path?: Keyframe[];
}

export interface AssetManifest {
  materials?: any[];
  furniture?: any[];
}

export interface ComplianceData {
  compliant: boolean;
  issues: string[];
  actual_far?: number;
  allowed_far?: number;
  actual_coverage_pct?: number;
  allowed_coverage_pct?: number;
  vastu_suggestions?: string[];
  seismic_guideline?: string;
}

export interface PlacedAsset {
  placement_id: string;
  asset_uid: string;
  position: [number, number, number];
  rotation: [number, number, number];
  scale: number;
  glb_url?: string;
  local_path?: string;
  name?: string;
}

export type ProjectionType =
  | "perspective_1p"
  | "perspective_2p"
  | "perspective_3p"
  | "orthographic_top"
  | "orthographic_front"
  | "orthographic_side"
  | "isometric"
  | "oblique_cavalier"
  | "oblique_cabinet";

// FIXED: Match backend component_group names exactly
export type ComponentGroupFilter =
  | "All"
  | "Foundation"
  | "Structure"      // was "Floor Slabs"
  | "Exterior"       // was "Walls"
  | "Windows"
  | "Roof"
  | "Entrance"
  | "Pool"
  | "Landscape"
  | "Boundary"
  | "Chimney"
  | "Garage";

interface ArchitectStore {
  projectId: string;
  clientId: string;
  currentPrompt: string;
  isGenerating: boolean;
  agentLogs: AgentUpdate[];
  geometryData: GeometryData | null;
  sceneConfig: SceneConfig | null;
  assetManifest: AssetManifest | null;
  dronePath: Keyframe[] | null;
  isDroneFlying: boolean;
  currentDroneKeyframe: number;

  // Plot
  plotLat: number;
  plotLng: number;
  plotWidth: number;
  plotDepth: number;

  // View controls
  activeProjection: ProjectionType;
  visibleComponentGroup: ComponentGroupFilter;
  complianceData: ComplianceData | null;

  // NEW: Asset placement state
  placedAssets: PlacedAsset[];
  selectedAssetUid: string | null;
  isAssetPaletteOpen: boolean;

  // Actions
  setProjectId: (id: string) => void;
  setPrompt: (prompt: string) => void;
  setIsGenerating: (generating: boolean) => void;
  addAgentLog: (log: AgentUpdate) => void;
  clearAgentLogs: () => void;
  updateScene: (geometry: GeometryData, config: SceneConfig, assets: AssetManifest, compliance?: ComplianceData) => void;
  setDroneFlying: (flying: boolean) => void;
  setDroneKeyframe: (index: number) => void;
  setPlotData: (lat: number, lng: number, w: number, d: number) => void;
  setActiveProjection: (proj: ProjectionType) => void;
  setVisibleComponentGroup: (group: ComponentGroupFilter) => void;
  setComplianceData: (data: ComplianceData | null) => void;

  // NEW: Asset actions
  addPlacedAsset: (asset: PlacedAsset) => void;
  removePlacedAsset: (placement_id: string) => void;
  updatePlacedAsset: (placement_id: string, updates: Partial<PlacedAsset>) => void;
  setSelectedAssetUid: (uid: string | null) => void;
  setAssetPaletteOpen: (open: boolean) => void;
  clearPlacedAssets: () => void;
}

export const useStore = create<ArchitectStore>((set) => ({
  projectId: "default-project",
  clientId: typeof window !== "undefined" ? Math.random().toString(36).substring(7) : "server",
  currentPrompt: "",
  isGenerating: false,
  agentLogs: [],
  geometryData: null,
  sceneConfig: null,
  assetManifest: null,
  dronePath: null,
  isDroneFlying: false,
  currentDroneKeyframe: 0,

  plotLat: 19.0760,
  plotLng: 72.8777,
  plotWidth: 20.0,
  plotDepth: 30.0,
  activeProjection: "perspective_2p",
  visibleComponentGroup: "All",
  complianceData: null,

  // NEW defaults
  placedAssets: [],
  selectedAssetUid: null,
  isAssetPaletteOpen: false,

  setProjectId: (id) => set({ projectId: id }),
  setPrompt: (prompt) => set({ currentPrompt: prompt }),
  setIsGenerating: (generating) => set({ isGenerating: generating }),
  addAgentLog: (log) => set((state) => ({ agentLogs: [...state.agentLogs, log] })),
  clearAgentLogs: () => set({ agentLogs: [] }),
  updateScene: (geometry, config, assets, compliance) => set({
    geometryData: geometry,
    sceneConfig: config,
    assetManifest: assets,
    dronePath: config?.drone_path || null,
    complianceData: compliance || null
  }),
  setDroneFlying: (flying) => set({ isDroneFlying: flying }),
  setDroneKeyframe: (index) => set({ currentDroneKeyframe: index }),
  setPlotData: (lat, lng, w, d) => set({ plotLat: lat, plotLng: lng, plotWidth: w, plotDepth: d }),
  setActiveProjection: (proj) => set({ activeProjection: proj }),
  setVisibleComponentGroup: (group) => set({ visibleComponentGroup: group }),
  setComplianceData: (data) => set({ complianceData: data }),

  // NEW asset actions
  addPlacedAsset: (asset) => set((state) => ({
    placedAssets: [...state.placedAssets, asset]
  })),
  removePlacedAsset: (placement_id) => set((state) => ({
    placedAssets: state.placedAssets.filter((a) => a.placement_id !== placement_id)
  })),
  updatePlacedAsset: (placement_id, updates) => set((state) => ({
    placedAssets: state.placedAssets.map((a) =>
      a.placement_id === placement_id ? { ...a, ...updates } : a
    )
  })),
  setSelectedAssetUid: (uid) => set({ selectedAssetUid: uid }),
  setAssetPaletteOpen: (open) => set({ isAssetPaletteOpen: open }),
  clearPlacedAssets: () => set({ placedAssets: [] })
}));
