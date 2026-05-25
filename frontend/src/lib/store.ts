import { create } from "zustand";

// ─── Types ─────────────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "agent";
  content: string;
  timestamp: number;
  agentName?: string;
  isStreaming?: boolean;
  buildingSummary?: {
    type: string; floors: number; features: string[];
    compliant: boolean; far?: number; coverage?: number;
  };
}

export interface AgentUpdate { agent: string; message: string; data?: any; }
export interface Room { id: string; name: string; x: number; y: number; width_m: number; height_m: number; }
export interface Mesh {
  id: string; component_group: string; type: string;
  position: [number,number,number]; scale: [number,number,number];
  rotation?: [number,number,number]; material_id: string;
}
export interface GeometryData { meshes?: Mesh[]; rooms?: Room[]; style?: string; total_height_m?: number; }
export interface CameraConfig { type: string; fov: number; position: [number,number,number]; target: [number,number,number]; }
export interface Keyframe { index: number; position: [number,number,number]; look_at: [number,number,number]; duration_s: number; }
export interface SceneConfig { camera?: CameraConfig; lighting?: any[]; drone_path?: Keyframe[]; }
export interface AssetManifest { materials?: any[]; furniture?: any[]; }
export interface ComplianceData {
  compliant: boolean; issues: string[];
  actual_far?: number; allowed_far?: number;
  actual_coverage_pct?: number; allowed_coverage_pct?: number;
  vastu_suggestions?: string[]; seismic_guideline?: string;
}

export type ProjectionType =
  | "perspective_1p" | "perspective_2p" | "perspective_3p"
  | "orthographic_top" | "orthographic_front" | "orthographic_side"
  | "isometric" | "oblique_cavalier" | "oblique_cabinet";

export type ComponentGroupFilter = "All" | "Foundation" | "Floor Slabs" | "Walls" | "Windows" | "Roof";
export type OutputMode = "fast_preview" | "high_quality" | "photorealistic";

export interface ArtifactInfo {
  id: string; stage: string; url?: string;
  thumbnail?: string; status: string; created_at?: string;
}

// ─── Store ─────────────────────────────────────────────────────────────────

interface ArchitectStore {
  projectId: string; clientId: string;
  currentPrompt: string; isGenerating: boolean;
  // Chat
  chatMessages: ChatMessage[];
  addChatMessage: (msg: Omit<ChatMessage, "id" | "timestamp">) => string;
  updateChatMessage: (id: string, patch: Partial<ChatMessage>) => void;
  clearChat: () => void;
  // Agent logs (kept for backward compat)
  agentLogs: AgentUpdate[];
  addAgentLog: (log: AgentUpdate) => void;
  clearAgentLogs: () => void;
  // Scene
  geometryData: GeometryData | null;
  sceneConfig: SceneConfig | null;
  assetManifest: AssetManifest | null;
  dronePath: Keyframe[] | null;
  isDroneFlying: boolean;
  currentDroneKeyframe: number;
  plotLat: number; plotLng: number; plotWidth: number; plotDepth: number;
  activeProjection: ProjectionType;
  visibleComponentGroup: ComponentGroupFilter;
  complianceData: ComplianceData | null;
  // Artifacts
  activeOutputMode: OutputMode;
  artifacts: ArtifactInfo[];
  artifactGenerationStatus: "idle" | "generating" | "completed" | "failed";
  designStyle: string;
  designStyles: { id: string; name: string; description: string }[];
  // Actions
  setProjectId: (id: string) => void;
  setPrompt: (prompt: string) => void;
  setIsGenerating: (generating: boolean) => void;
  updateScene: (geometry: GeometryData, config: SceneConfig, assets: AssetManifest, compliance?: ComplianceData) => void;
  setDroneFlying: (flying: boolean) => void;
  setDroneKeyframe: (index: number) => void;
  setPlotData: (lat: number, lng: number, w: number, d: number) => void;
  setActiveProjection: (proj: ProjectionType) => void;
  setVisibleComponentGroup: (group: ComponentGroupFilter) => void;
  setComplianceData: (data: ComplianceData | null) => void;
  setActiveOutputMode: (mode: OutputMode) => void;
  setArtifacts: (artifacts: ArtifactInfo[]) => void;
  setArtifactGenerationStatus: (status: "idle" | "generating" | "completed" | "failed") => void;
  addArtifact: (artifact: ArtifactInfo) => void;
  setDesignStyle: (style: string) => void;
  setDesignStyles: (styles: { id: string; name: string; description: string }[]) => void;
}

export const useStore = create<ArchitectStore>((set) => ({
  projectId: "default-project",
  clientId: typeof window !== "undefined" ? Math.random().toString(36).substring(7) : "server",
  currentPrompt: "", isGenerating: false,

  chatMessages: [{
    id: "welcome", role: "assistant",
    content: "Hello! I'm your AI Architect. Describe what you want to build — style, floors, features like pool or garage — and I'll generate it in 3D with Indian NBC compliance checks.\n\n**Try:** *\"Modern 3-floor villa with pool, glass windows and red brick walls\"*",
    timestamp: Date.now(),
  }],
  addChatMessage: (msg) => {
    const id = Math.random().toString(36).slice(2);
    set((s) => ({ chatMessages: [...s.chatMessages, { ...msg, id, timestamp: Date.now() }] }));
    return id;
  },
  updateChatMessage: (id, patch) =>
    set((s) => ({ chatMessages: s.chatMessages.map((m) => m.id === id ? { ...m, ...patch } : m) })),
  clearChat: () => set({ chatMessages: [] }),

  agentLogs: [],
  addAgentLog: (log) => set((s) => ({ agentLogs: [...s.agentLogs, log] })),
  clearAgentLogs: () => set({ agentLogs: [] }),

  geometryData: null, sceneConfig: null, assetManifest: null,
  dronePath: null, isDroneFlying: false, currentDroneKeyframe: 0,
  plotLat: 19.0760, plotLng: 72.8777, plotWidth: 20.0, plotDepth: 30.0,
  activeProjection: "perspective_2p", visibleComponentGroup: "All", complianceData: null,
  activeOutputMode: "fast_preview", artifacts: [], artifactGenerationStatus: "idle",
  designStyle: "modern", designStyles: [],

  setProjectId: (id) => set({ projectId: id }),
  setPrompt: (prompt) => set({ currentPrompt: prompt }),
  setIsGenerating: (generating) => set({ isGenerating: generating }),
  updateScene: (geometry, config, assets, compliance) => set({
    geometryData: geometry, sceneConfig: config, assetManifest: assets,
    dronePath: config?.drone_path || null, complianceData: compliance || null,
  }),
  setDroneFlying: (flying) => set({ isDroneFlying: flying }),
  setDroneKeyframe: (index) => set({ currentDroneKeyframe: index }),
  setPlotData: (lat, lng, w, d) => set({ plotLat: lat, plotLng: lng, plotWidth: w, plotDepth: d }),
  setActiveProjection: (proj) => set({ activeProjection: proj }),
  setVisibleComponentGroup: (group) => set({ visibleComponentGroup: group }),
  setComplianceData: (data) => set({ complianceData: data }),
  setActiveOutputMode: (mode) => set({ activeOutputMode: mode }),
  setArtifacts: (artifacts) => set({ artifacts }),
  setArtifactGenerationStatus: (status) => set({ artifactGenerationStatus: status }),
  addArtifact: (artifact) => set((s) => ({ artifacts: [...s.artifacts.filter(a => a.stage !== artifact.stage), artifact] })),
  setDesignStyle: (style) => set({ designStyle: style }),
  setDesignStyles: (styles) => set({ designStyles: styles }),
}));
