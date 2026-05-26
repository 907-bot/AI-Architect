"use client";

import React, { useEffect, useRef, useCallback, useState, Suspense } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Grid, ContactShadows, Environment, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { useStore } from "@/lib/store";

// ====================================================
// TYPES
// ====================================================

interface PlacedAsset {
  placement_id: string;
  asset_uid: string;
  position: [number, number, number];
  rotation: [number, number, number];
  scale: number;
  glb_url?: string;
  local_path?: string;
  name?: string;
}

// ====================================================
// SKETCHFAB GLB LOADER
// ====================================================

function SketchfabModel({
  url, position, rotation, scale,
}: {
  url: string;
  position: [number, number, number];
  rotation: [number, number, number];
  scale: number;
}) {
  const { scene } = useGLTF(url, true);
  const ref = useRef<THREE.Group>(null);

  useEffect(() => {
    if (!ref.current) return;
    const box = new THREE.Box3().setFromObject(ref.current);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const ns = maxDim > 0 ? scale / maxDim : scale;
    ref.current.scale.setScalar(ns);
    ref.current.position.set(position[0], position[1], position[2]);
    ref.current.rotation.set(rotation[0], rotation[1], rotation[2]);
    ref.current.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
        const mat = (child as THREE.Mesh).material as THREE.MeshStandardMaterial;
        if (mat) mat.envMapIntensity = 1.2;
      }
    });
  }, [url, position, rotation, scale]);

  return <primitive ref={ref} object={scene.clone()} />;
}

// ====================================================
// PROCEDURAL BUILDING
// ====================================================

function ProceduralBuilding() {
  const geometryData = useStore((s) => s.geometryData);
  const assetManifest = useStore((s) => s.assetManifest);
  const filter = useStore((s) => s.visibleComponentGroup);

  if (!geometryData?.meshes) return null;

  const filteredMeshes = geometryData.meshes.filter((mesh) => {
    if (filter === "All") return true;
    const mapping: Record<string, string[]> = {
      Foundation: ["Foundation"],
      Structure: ["Structure"],
      Exterior: ["Exterior"],
      Windows: ["Windows"],
      Roof: ["Roof"],
      Entrance: ["Entrance"],
      Pool: ["Pool"],
      Landscape: ["Landscape"],
      Boundary: ["Boundary"],
      Chimney: ["Chimney"],
      Garage: ["Garage"],
    };
    return (mapping[filter] || [filter]).includes(mesh.component_group);
  });

  return (
    <group>
      {filteredMeshes.map((mesh) => {
        const mat = assetManifest?.materials?.find(
          (m: any) => m.material_id === mesh.material_id || m.id === mesh.material_id
        );
        return (
          <mesh
            key={mesh.id}
            position={mesh.position}
            scale={mesh.scale}
            rotation={mesh.rotation || [0, 0, 0]}
            castShadow receiveShadow
          >
            <boxGeometry />
            <meshStandardMaterial
              color={mat?.color_hex || mat?.color || "#cbd5e1"}
              roughness={mat?.roughness ?? 0.8}
              metalness={mat?.metallic ?? 0.1}
            />
          </mesh>
        );
      })}
    </group>
  );
}

// ====================================================
// PLACED ASSETS RENDERER
// ====================================================

function PlacedAssets({ assets }: { assets: PlacedAsset[] }) {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://ai-architect-production-1e57.up.railway.app";

  return (
    <group>
      {assets.map((asset) => {
        // Build URL: prefer local cached GLB, fallback to remote URL
        let url = asset.glb_url || "";
        if (asset.local_path) {
          const filename = asset.local_path.split("/").pop();
          url = `${API_BASE}/cache/sketchfab/${filename}`;
        }
        if (!url) return null;

        return (
          <Suspense
            key={asset.placement_id}
            fallback={
              <mesh position={asset.position}>
                <boxGeometry args={[0.8, 0.8, 0.8]} />
                <meshStandardMaterial color="#3b82f6" wireframe />
              </mesh>
            }
          >
            <SketchfabModel
              url={url}
              position={asset.position}
              rotation={asset.rotation}
              scale={asset.scale}
            />
          </Suspense>
        );
      })}
    </group>
  );
}

// ====================================================
// FLOOR PLANE (invisible, used for drop raycasting)
// ====================================================

function FloorPlane({ planeRef }: { planeRef: React.RefObject<THREE.Mesh> }) {
  return (
    <mesh ref={planeRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} visible={false}>
      <planeGeometry args={[200, 200]} />
      <meshBasicMaterial />
    </mesh>
  );
}

// ====================================================
// CAMERA CONTROLLER
// ====================================================

function CameraController() {
  const { camera, size } = useThree();
  const proj = useStore((s) => s.activeProjection);
  const dronePath = useStore((s) => s.dronePath);
  const isDrone = useStore((s) => s.isDroneFlying);
  const kf = useStore((s) => s.currentDroneKeyframe);
  const setKf = useStore((s) => s.setDroneKeyframe);
  const progress = useRef(0);

  useEffect(() => {
    const isOrtho = proj.startsWith("orthographic") || proj === "isometric" || proj.startsWith("oblique");
    if (isOrtho) {
      const asp = size.width / size.height;
      const fs = 28;
      const o = new THREE.OrthographicCamera(-fs * asp / 2, fs * asp / 2, fs / 2, -fs / 2, 0.1, 500);
      if (proj === "orthographic_top") o.position.set(0, 40, 0.01);
      else if (proj === "orthographic_front") o.position.set(0, 6, 40);
      else if (proj === "orthographic_side") o.position.set(40, 6, 0);
      else o.position.set(20, 20, 20);
      o.lookAt(0, 0, 0);
      camera.position.copy(o.position);
      camera.quaternion.copy(o.quaternion);
      camera.updateProjectionMatrix();
    } else {
      const pc = camera as THREE.PerspectiveCamera;
      pc.fov = proj === "perspective_1p" ? 42 : proj === "perspective_3p" ? 70 : 60;
      if (proj === "perspective_1p") { pc.position.set(0, 3.5, 22); pc.lookAt(0, 3.5, 0); }
      else if (proj === "perspective_3p") { pc.position.set(20, 22, 20); pc.lookAt(0, 2, 0); }
      else { pc.position.set(15, 12, 15); pc.lookAt(0, 1.5, 0); }
      pc.updateProjectionMatrix();
    }
  }, [proj, size, camera]);

  useFrame((_, dt) => {
    if (!isDrone || !dronePath?.length) return;
    const cur = dronePath[kf];
    const nxt = dronePath[(kf + 1) % dronePath.length];
    progress.current += dt / (cur.duration_s || 4);
    const t = Math.min(progress.current, 1);
    camera.position.lerpVectors(new THREE.Vector3(...cur.position), new THREE.Vector3(...nxt.position), t);
    camera.lookAt(new THREE.Vector3(...(cur.look_at || [0, 2, 0])));
    if (t >= 1) { progress.current = 0; setKf((kf + 1) % dronePath.length); }
  });

  return null;
}

// ====================================================
// GROUND
// ====================================================

function Ground() {
  const pw = useStore((s) => s.plotWidth);
  const pd = useStore((s) => s.plotDepth);
  const r = Math.max(pw, pd) * 0.9;
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
        <circleGeometry args={[r, 64]} />
        <meshStandardMaterial color="#3a3a3a" roughness={0.9} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.005, 0]} receiveShadow>
        <circleGeometry args={[r * 0.85, 64]} />
        <meshStandardMaterial color="#2d5a1e" roughness={1} />
      </mesh>
    </group>
  );
}

// ====================================================
// RAYCASTER HOOK — translates HTML drop coords → 3D point
// ====================================================

function useDropRaycaster(
  canvasRef: React.RefObject<HTMLDivElement>,
  floorRef: React.RefObject<THREE.Mesh>,
  cameraRef: React.RefObject<THREE.Camera>
) {
  return useCallback((clientX: number, clientY: number): THREE.Vector3 => {
    if (!canvasRef.current || !floorRef.current || !cameraRef.current) {
      return new THREE.Vector3(0, 0, 0);
    }
    const rect = canvasRef.current.getBoundingClientRect();
    const x = ((clientX - rect.left) / rect.width) * 2 - 1;
    const y = -((clientY - rect.top) / rect.height) * 2 + 1;
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(new THREE.Vector2(x, y), cameraRef.current);
    const hits = raycaster.intersectObject(floorRef.current);
    return hits.length > 0 ? hits[0].point : new THREE.Vector3(0, 0, 0);
  }, [canvasRef, floorRef, cameraRef]);
}

// ====================================================
// MAIN VIEWER
// ====================================================

export default function ThreeJSViewer() {
  const isDroneFlying = useStore((s) => s.isDroneFlying);
  const activeProjection = useStore((s) => s.activeProjection);
  const isAssetPaletteOpen = useStore((s) => s.isAssetPaletteOpen);
  const setAssetPaletteOpen = useStore((s) => s.setAssetPaletteOpen);

  const [placedAssets, setPlacedAssets] = useState<PlacedAsset[]>([]);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [dropStatus, setDropStatus] = useState<string | null>(null);

  const canvasWrapperRef = useRef<HTMLDivElement>(null);
  const floorRef = useRef<THREE.Mesh>(null);
  const cameraRef = useRef<THREE.Camera | null>(null);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://ai-architect-production-1e57.up.railway.app";

  const enableOrbit = !isDroneFlying &&
    !activeProjection.startsWith("orthographic") &&
    !activeProjection.startsWith("oblique");

  // ── HTML drag events on the canvas wrapper div ──────────────────────────────

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    setIsDraggingOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    // Only fire if leaving the canvas entirely
    if (!canvasWrapperRef.current?.contains(e.relatedTarget as Node)) {
      setIsDraggingOver(false);
    }
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDraggingOver(false);

    // Read asset data from dataTransfer (set by AssetPalette)
    let raw = e.dataTransfer.getData("application/json");
    if (!raw) raw = e.dataTransfer.getData("text/plain");

    // Fallback to window global if dataTransfer is empty (some browser quirks)
    if (!raw && (window as any).__draggedAsset) {
      raw = JSON.stringify((window as any).__draggedAsset);
    }
    delete (window as any).__draggedAsset;

    if (!raw) {
      console.warn("No drag data found");
      return;
    }

    let dragData: { uid: string; name: string; source: string };
    try {
      dragData = JSON.parse(raw);
    } catch {
      console.error("Bad drag JSON:", raw);
      return;
    }

    // Raycast drop position onto floor plane
    let dropPos = { x: 0, y: 0, z: 0 };
    if (canvasWrapperRef.current && floorRef.current && cameraRef.current) {
      const rect = canvasWrapperRef.current.getBoundingClientRect();
      const nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const ny = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(nx, ny), cameraRef.current);
      const hits = raycaster.intersectObject(floorRef.current);
      if (hits.length > 0) {
        dropPos = { x: hits[0].point.x, y: 0, z: hits[0].point.z };
      } else {
        // Fallback: random position near center
        dropPos = { x: (Math.random() - 0.5) * 10, y: 0, z: (Math.random() - 0.5) * 10 };
      }
    }

    setDropStatus(`Placing ${dragData.name}...`);

    try {
      const resp = await fetch(`${API_BASE}/api/sketchfab/drag-drop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_uid: dragData.uid,
          drop_position: dropPos,
          surface_normal: { x: 0, y: 1, z: 0 },
          room_context: "interior",
          auto_orient: true,
          auto_scale: true,
        }),
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const placement = await resp.json();

      if (placement.placement_id) {
        setPlacedAssets((prev) => [
          ...prev,
          {
            placement_id: placement.placement_id,
            asset_uid: placement.asset_uid,
            position: [placement.position.x, placement.position.y, placement.position.z],
            rotation: [placement.rotation.x || 0, placement.rotation.y || 0, placement.rotation.z || 0],
            scale: placement.scale || 1,
            glb_url: placement.glb_url,
            local_path: placement.local_path,
            name: dragData.name,
          },
        ]);
        setDropStatus(`✓ ${dragData.name} placed`);
        setTimeout(() => setDropStatus(null), 2500);
      }
    } catch (err) {
      console.error("Drop placement failed:", err);
      setDropStatus("Drop failed — check console");
      setTimeout(() => setDropStatus(null), 3000);
    }
  }, [API_BASE]);

  return (
    <div className="relative w-full h-full">
      {/* Toggle Asset Palette button */}
      <button
        onClick={() => setAssetPaletteOpen(!isAssetPaletteOpen)}
        className="absolute top-4 left-4 z-20 bg-neutral-800 hover:bg-neutral-700 border border-neutral-600 text-white text-xs px-3 py-2 rounded-lg transition flex items-center gap-2 shadow-lg"
      >
        <span>{isAssetPaletteOpen ? "◀ Hide Assets" : "▶ Asset Library"}</span>
      </button>

      {/* Drop status toast */}
      {dropStatus && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 bg-neutral-900/95 border border-blue-500/50 text-white text-xs px-4 py-2 rounded-lg shadow-xl">
          {dropStatus}
        </div>
      )}

      {/* Placed asset count */}
      {placedAssets.length > 0 && (
        <div className="absolute bottom-4 right-4 z-20 flex items-center gap-2">
          <div className="bg-neutral-900/90 border border-neutral-700 rounded-lg px-3 py-1.5 text-xs text-white">
            {placedAssets.length} asset{placedAssets.length !== 1 ? "s" : ""} placed
          </div>
          <button
            onClick={() => setPlacedAssets([])}
            className="bg-neutral-900/90 border border-red-700/50 text-red-400 hover:text-red-300 rounded-lg px-2 py-1.5 text-xs transition"
          >
            Clear
          </button>
        </div>
      )}

      {/* Canvas wrapper — this div receives native drag events */}
      <div
        ref={canvasWrapperRef}
        className={`w-full h-full transition-all ${isDraggingOver ? "ring-2 ring-blue-500 ring-inset" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Drop overlay hint */}
        {isDraggingOver && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10 bg-blue-500/10">
            <div className="bg-neutral-900/90 border border-blue-500/50 rounded-xl px-6 py-4 text-center">
              <p className="text-blue-400 font-semibold text-sm">Drop to place asset</p>
              <p className="text-neutral-500 text-xs mt-1">Model will be downloaded & placed in scene</p>
            </div>
          </div>
        )}

        <Canvas
          shadows
          camera={{ position: [15, 12, 15], fov: 60 }}
          gl={{ antialias: true, alpha: false, toneMapping: THREE.ACESFilmicToneMapping }}
          onCreated={({ gl, camera }) => {
            gl.setClearColor("#0a0a0a");
            gl.shadowMap.enabled = true;
            gl.shadowMap.type = THREE.PCFSoftShadowMap;
            // Store camera ref for drop raycasting
            cameraRef.current = camera;
          }}
        >
          <color attach="background" args={["#0a0a0a"]} />
          <fog attach="fog" args={["#0a0a0a", 30, 90]} />

          <ambientLight intensity={0.4} />
          <hemisphereLight intensity={0.3} groundColor="#1a1a1a" />
          <directionalLight
            position={[10, 20, 10]}
            intensity={1.5}
            castShadow
            shadow-mapSize-width={2048}
            shadow-mapSize-height={2048}
            shadow-camera-far={60}
            shadow-camera-left={-25}
            shadow-camera-right={25}
            shadow-camera-top={25}
            shadow-camera-bottom={-25}
          />

          <Environment preset="city" />
          <ContactShadows position={[0, 0.01, 0]} opacity={0.4} scale={50} blur={2} />

          <CameraController />
          <Ground />
          <ProceduralBuilding />
          <PlacedAssets assets={placedAssets} />

          {/* Invisible floor plane for raycasting drop position */}
          <FloorPlane planeRef={floorRef} />

          {enableOrbit && <OrbitControls makeDefault target={[0, 1.5, 0]} maxPolarAngle={Math.PI / 2} />}
          <Grid
            position={[0, 0, 0]}
            args={[100, 100]}
            cellSize={1}
            cellColor="#333"
            sectionSize={5}
            sectionColor="#444"
            fadeDistance={40}
          />
        </Canvas>
      </div>
    </div>
  );
}
