"use client";

import React, { useEffect, useRef, useCallback, useState, Suspense } from "react";
import { Canvas, useFrame, useThree, useLoader } from "@react-three/fiber";
import { OrbitControls, Grid, ContactShadows, Environment, Center, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { useStore, ProjectionType, ComponentGroupFilter } from "@/lib/store";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

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

interface DropZoneProps {
  onDrop: (position: THREE.Vector3, normal: THREE.Vector3) => void;
}

// ====================================================
// SKETCHFAB GLB LOADER COMPONENT
// ====================================================

function SketchfabModel({
  url,
  position,
  rotation,
  scale,
  onLoad
}: {
  url: string;
  position: [number, number, number];
  rotation: [number, number, number];
  scale: number;
  onLoad?: () => void;
}) {
  // Use drei's useGLTF for cached loading
  const { scene } = useGLTF(url, true);
  const modelRef = useRef<THREE.Group>(null);

  useEffect(() => {
    if (modelRef.current) {
      // Center and normalize the model
      const box = new THREE.Box3().setFromObject(modelRef.current);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z);
      const normalizeScale = maxDim > 0 ? 1 / maxDim : 1;

      modelRef.current.position.set(
        position[0] - center.x * normalizeScale * scale,
        position[1],
        position[2] - center.z * normalizeScale * scale
      );
      modelRef.current.rotation.set(rotation[0], rotation[1], rotation[2]);
      modelRef.current.scale.setScalar(normalizeScale * scale);

      // Apply PBR material fixes
      modelRef.current.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh;
          mesh.castShadow = true;
          mesh.receiveShadow = true;
          if (mesh.material) {
            const mat = mesh.material as THREE.MeshStandardMaterial;
            mat.envMapIntensity = 1.2;
          }
        }
      });

      onLoad?.();
    }
  }, [scene, position, rotation, scale, onLoad]);

  return <primitive ref={modelRef} object={scene.clone()} />;
}

// ====================================================
// DROP ZONE — Invisible plane that accepts drag-and-drop
// ====================================================

function DropZone({ onDrop }: DropZoneProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handlePointerOver = useCallback((e: any) => {
    e.stopPropagation();
    if (e.nativeEvent.dataTransfer?.types.includes("application/json")) {
      setIsDragOver(true);
    }
  }, []);

  const handlePointerOut = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: any) => {
    e.stopPropagation();
    setIsDragOver(false);

    const data = e.nativeEvent.dataTransfer?.getData("application/json");
    if (!data) return;

    try {
      const asset = JSON.parse(data);
      // Raycast to get exact drop position
      const raycaster = new THREE.Raycaster();
      const mouse = new THREE.Vector2(
        (e.nativeEvent.offsetX / window.innerWidth) * 2 - 1,
        -(e.nativeEvent.offsetY / window.innerHeight) * 2 + 1
      );
      // Use the intersection point from the event
      const point = e.point;
      const normal = e.face?.normal || new THREE.Vector3(0, 1, 0);

      onDrop(point, normal);
    } catch (err) {
      console.error("Drop error:", err);
    }
  }, [onDrop]);

  return (
    <mesh
      ref={meshRef}
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, 0.01, 0]}
      onPointerOver={handlePointerOver}
      onPointerOut={handlePointerOut}
      onDrop={handleDrop}
      visible={isDragOver}
    >
      <planeGeometry args={[100, 100]} />
      <meshBasicMaterial color="#3b82f6" transparent opacity={0.15} side={THREE.DoubleSide} />
    </mesh>
  );
}

// ====================================================
// PROCEDURAL BUILDING (with component filtering)
// ====================================================

function ProceduralBuilding() {
  const geometryData = useStore((state) => state.geometryData);
  const assetManifest = useStore((state) => state.assetManifest);
  const filter = useStore((state) => state.visibleComponentGroup);

  if (!geometryData?.meshes) return null;

  const filteredMeshes = geometryData.meshes.filter((mesh) => {
    if (filter === "All") return true;
    // Map frontend filter names to backend group names
    const mapping: Record<string, string[]> = {
      "Foundation": ["Foundation"],
      "Floor Slabs": ["Structure"],
      "Walls": ["Exterior"],
      "Windows": ["Windows"],
      "Roof": ["Roof"],
      "Entrance": ["Entrance"],
      "Pool": ["Pool"],
      "Landscape": ["Landscape"],
      "Boundary": ["Boundary"]
    };
    const allowed = mapping[filter] || [filter];
    return allowed.includes(mesh.component_group);
  });

  return (
    <group>
      {filteredMeshes.map((mesh) => {
        const materialId = mesh.material_id;
        const matchingMaterial = assetManifest?.materials?.find(
          (m: any) => m.material_id === materialId || m.id === materialId
        );
        const color = matchingMaterial?.color_hex || matchingMaterial?.color || "#cbd5e1";
        const roughness = matchingMaterial?.roughness ?? 0.8;
        const metallic = matchingMaterial?.metallic ?? 0.1;

        return (
          <mesh
            key={mesh.id}
            position={mesh.position}
            scale={mesh.scale}
            rotation={mesh.rotation || [0, 0, 0]}
            castShadow
            receiveShadow
          >
            <boxGeometry />
            <meshStandardMaterial
              color={color}
              roughness={roughness}
              metalness={metallic}
            />
          </mesh>
        );
      })}
    </group>
  );
}

// ====================================================
// PLACED ASSETS (Sketchfab models + user uploads)
// ====================================================

function PlacedAssets({
  assets,
  onAssetLoad
}: {
  assets: PlacedAsset[];
  onAssetLoad?: (id: string) => void;
}) {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://ai-architect-production-1e57.up.railway.app";

  return (
    <group>
      {assets.map((asset) => {
        const url = asset.local_path
          ? `${API_BASE}/cache/sketchfab/${asset.local_path.split("/").pop()}`
          : asset.glb_url;

        if (!url) return null;

        return (
          <Suspense
            key={asset.placement_id}
            fallback={
              <mesh position={asset.position}>
                <boxGeometry args={[0.5, 0.5, 0.5]} />
                <meshBasicMaterial color="#3b82f6" wireframe />
              </mesh>
            }
          >
            <SketchfabModel
              url={url}
              position={asset.position}
              rotation={[
                asset.rotation.x || 0,
                asset.rotation.y || 0,
                asset.rotation.z || 0
              ]}
              scale={asset.scale}
              onLoad={() => onAssetLoad?.(asset.placement_id)}
            />
          </Suspense>
        );
      })}
    </group>
  );
}

// ====================================================
// CAMERA CONTROLLER (with projections + drone)
// ====================================================

function ProjectionCameraController() {
  const { camera, size } = useThree();
  const activeProjection = useStore((state) => state.activeProjection);
  const dronePath = useStore((state) => state.dronePath);
  const isDroneFlying = useStore((state) => state.isDroneFlying);
  const currentKeyframe = useStore((state) => state.currentDroneKeyframe);
  const setDroneKeyframe = useStore((state) => state.setDroneKeyframe);
  const progressRef = useRef(0);

  useEffect(() => {
    if (activeProjection.startsWith("orthographic") || activeProjection === "isometric" || activeProjection.startsWith("oblique")) {
      const aspect = size.width / size.height;
      const frustumSize = 0.6;
      const orthoCam = new THREE.OrthographicCamera(
        frustumSize * aspect / -2, frustumSize * aspect / 2,
        frustumSize / 2, frustumSize / -2, 0.1, 1000
      );

      if (activeProjection === "orthographic_top") {
        orthoCam.position.set(0, 30, 0);
      } else if (activeProjection === "orthographic_front") {
        orthoCam.position.set(0, 5, 30);
      } else if (activeProjection === "orthographic_side") {
        orthoCam.position.set(30, 5, 0);
      } else if (activeProjection === "isometric") {
        orthoCam.position.set(15, 15, 15);
      }
      orthoCam.lookAt(0, 0, 0);

      camera.position.copy(orthoCam.position);
      if (camera instanceof THREE.OrthographicCamera) {
        Object.assign(camera, orthoCam);
      }
      camera.updateProjectionMatrix();
    } else {
      Object.setPrototypeOf(camera, THREE.PerspectiveCamera.prototype);
      const persCam = camera as THREE.PerspectiveCamera;
      persCam.fov = activeProjection === "perspective_1p" ? 40 : 60;
      if (activeProjection === "perspective_1p") {
        persCam.position.set(0, 2.5, 18);
      } else if (activeProjection === "perspective_3p") {
        persCam.position.set(18, 20, 18);
      } else if (activeProjection === "perspective_2p" && !isDroneFlying) {
        persCam.position.set(15, 12, 15);
      }
      persCam.lookAt(0, 1.5, 0);
      persCam.updateProjectionMatrix();
    }
  }, [activeProjection, size, camera, isDroneFlying]);

  useFrame((state, delta) => {
    if (!isDroneFlying || !dronePath?.length) return;
    const currentKf = dronePath[currentKeyframe];
    const nextKfIndex = (currentKeyframe + 1) % dronePath.length;
    const nextKf = dronePath[nextKfIndex];
    const duration = currentKf.duration_s || 3;
    progressRef.current += delta / duration;

    const startPos = new THREE.Vector3(...currentKf.position);
    const endPos = new THREE.Vector3(...nextKf.position);
    const newPos = new THREE.Vector3().lerpVectors(startPos, endPos, Math.min(progressRef.current, 1));
    camera.position.copy(newPos);

    const startLook = new THREE.Vector3(...(currentKf.look_at || [0, 0, 0]));
    const endLook = new THREE.Vector3(...(nextKf.look_at || [0, 0, 0]));
    const targetLook = new THREE.Vector3().lerpVectors(startLook, endLook, Math.min(progressRef.current, 1));
    camera.lookAt(targetLook);

    if (progressRef.current >= 1) {
      progressRef.current = 0;
      setDroneKeyframe(nextKfIndex);
    }
  });

  return null;
}

// ====================================================
// PLOT / GROUND
// ====================================================

function PlotLand() {
  const plotWidth = useStore((state) => state.plotWidth);
  const plotDepth = useStore((state) => state.plotDepth);
  const radius = Math.max(plotWidth || 20, plotDepth || 30) * 0.7;

  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow>
        <circleGeometry args={[radius, 64]} />
        <meshStandardMaterial color="#3a3a3a" roughness={0.9} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.04, 0]} receiveShadow>
        <circleGeometry args={[radius * 0.85, 64]} />
        <meshStandardMaterial color="#2d5a1e" roughness={1} />
      </mesh>
    </group>
  );
}

// ====================================================
// MAIN VIEWER
// ====================================================

export default function ThreeJSViewer() {
  const isDroneFlying = useStore((state) => state.isDroneFlying);
  const activeProjection = useStore((state) => state.activeProjection);
  const geometryData = useStore((state) => state.geometryData);
  const [placedAssets, setPlacedAssets] = useState<PlacedAsset[]>([]);
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://ai-architect-production-1e57.up.railway.app";

  // Handle drop from AssetPalette
  const handleDrop = useCallback(async (point: THREE.Vector3, normal: THREE.Vector3) => {
    setIsDraggingOver(false);

    // Get dragged asset data from global (set by AssetPalette drag start)
    const dragData = (window as any).__draggedAsset;
    if (!dragData) return;

    try {
      const resp = await fetch(`${API_BASE}/api/assets/drag-drop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_uid: dragData.uid,
          drop_position: { x: point.x, y: point.y, z: point.z },
          surface_normal: { x: normal.x, y: normal.y, z: normal.z },
          room_context: "interior", // Detect from raycast hit
          auto_orient: true,
          auto_scale: true
        })
      });

      const placement = await resp.json();
      if (placement.placement_id) {
        setPlacedAssets(prev => [...prev, {
          placement_id: placement.placement_id,
          asset_uid: placement.asset_uid,
          position: [placement.position.x, placement.position.y, placement.position.z],
          rotation: [placement.rotation.x, placement.rotation.y, placement.rotation.z],
          scale: placement.scale,
          glb_url: placement.glb_url,
          local_path: placement.local_path,
          name: dragData.name
        }]);
      }
    } catch (e) {
      console.error("Drop placement failed:", e);
    }

    delete (window as any).__draggedAsset;
  }, [API_BASE]);

  // Listen for drag events on canvas container
  useEffect(() => {
    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
      setIsDraggingOver(true);
    };
    const handleDragLeave = () => setIsDraggingOver(false);
    const handleDropGlobal = (e: DragEvent) => {
      e.preventDefault();
      setIsDraggingOver(false);
    };

    window.addEventListener("dragover", handleDragOver);
    window.addEventListener("dragleave", handleDragLeave);
    window.addEventListener("drop", handleDropGlobal);
    return () => {
      window.removeEventListener("dragover", handleDragOver);
      window.removeEventListener("dragleave", handleDragLeave);
      window.removeEventListener("drop", handleDropGlobal);
    };
  }, []);

  const enableOrbit = !isDroneFlying && !activeProjection.startsWith("orthographic") && !activeProjection.startsWith("oblique");

  return (
    <div className={`relative w-full h-full ${isDraggingOver ? "ring-2 ring-blue-500 ring-inset" : ""}`}>
      <Canvas
        shadows
        camera={{ position: [15, 12, 15], fov: 60 }}
        gl={{ antialias: true, alpha: false }}
        onCreated={({ gl }) => {
          gl.setClearColor("#0a0a0a");
          gl.shadowMap.enabled = true;
          gl.shadowMap.type = THREE.PCFSoftShadowMap;
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
          shadow-camera-far={50}
          shadow-camera-left={-20}
          shadow-camera-right={20}
          shadow-camera-top={20}
          shadow-camera-bottom={-20}
        />

        <Environment preset="city" />
        <ContactShadows position={[0, 0.01, 0]} opacity={0.4} scale={50} blur={2} />

        <ProjectionCameraController />

        <PlotLand />
        <ProceduralBuilding />
        <PlacedAssets assets={placedAssets} />

        {/* Drop zone for drag-and-drop */}
        <DropZone onDrop={handleDrop} />

        {enableOrbit && <OrbitControls makeDefault target={[0, 1.5, 0]} />}
        <Grid position={[0, 0, 0]} args={[100, 100]} cellSize={1} cellColor="#333" sectionSize={5} sectionColor="#444" fadeDistance={40} />
      </Canvas>

      {/* Drop overlay */}
      {isDraggingOver && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none bg-blue-500/10">
          <div className="bg-neutral-900/90 border border-blue-500/50 rounded-xl px-6 py-4 text-center">
            <p className="text-blue-400 font-medium">Drop to place asset</p>
            <p className="text-neutral-500 text-xs mt-1">Release to position on surface</p>
          </div>
        </div>
      )}

      {/* Asset count badge */}
      {placedAssets.length > 0 && (
        <div className="absolute top-4 right-4 bg-neutral-900/80 border border-neutral-700 rounded-lg px-3 py-1.5 text-xs text-white">
          {placedAssets.length} asset{placedAssets.length > 1 ? "s" : ""} placed
        </div>
      )}
    </div>
  );
}
