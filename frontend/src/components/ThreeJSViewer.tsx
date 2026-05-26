"use client";

import React, { useEffect, useRef, Component, ErrorInfo, ReactNode, useMemo, useState, useCallback } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, ContactShadows, Environment, Sky, Html, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { useStore, PlacedAsset } from "@/lib/store";

// ─── Error Boundary ───────────────────────────────────────────────────────────
class MeshBoundary extends Component<{ children: ReactNode; fallback?: ReactNode }, { err: boolean }> {
  state = { err: false };
  static getDerivedStateFromError() { return { err: true }; }
  componentDidCatch(e: Error) { console.warn("R3F error:", e.message); }
  render() { return this.state.err ? (this.props.fallback ?? null) : this.props.children; }
}

// ─── Camera controller ────────────────────────────────────────────────────────
function CameraController() {
  const { camera, size } = useThree();
  const proj = useStore((s) => s.activeProjection);
  const dronePath = useStore((s) => s.dronePath);
  const isDrone = useStore((s) => s.isDroneFlying);
  const kf = useStore((s) => s.currentDroneKeyframe);
  const setKf = useStore((s) => s.setDroneKeyframe);
  const progress = useRef(0);

  useEffect(() => {
    try {
      if (proj.startsWith("orthographic") || proj === "isometric" || proj.startsWith("oblique")) {
        const asp = size.width / size.height;
        const fs = 28;
        if (proj === "orthographic_top") { camera.position.set(0, 40, 0.01); camera.lookAt(0, 0, 0); }
        else if (proj === "orthographic_front") { camera.position.set(0, 6, 40); camera.lookAt(0, 6, 0); }
        else if (proj === "orthographic_side") { camera.position.set(40, 6, 0); camera.lookAt(0, 6, 0); }
        else if (proj === "isometric") { camera.position.set(20, 20, 20); camera.lookAt(0, 2, 0); }
        else { camera.position.set(0, 6, 30); camera.lookAt(0, 6, 0); }
      } else {
        const pc = camera as THREE.PerspectiveCamera;
        if (proj === "perspective_1p") { pc.fov = 42; pc.position.set(0, 3.5, 22); pc.lookAt(0, 3.5, 0); }
        else if (proj === "perspective_3p") { pc.fov = 70; pc.position.set(20, 22, 20); pc.lookAt(0, 2, 0); }
        pc.updateProjectionMatrix();
      }
    } catch (e) { console.warn("cam err:", e); }
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

// ─── Ground ───────────────────────────────────────────────────────────────────
function Ground() {
  const pw = useStore((s) => s.plotWidth);
  const pd = useStore((s) => s.plotDepth);
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
        <circleGeometry args={[Math.max(pw, pd) * 3, 64]} />
        <meshStandardMaterial color="#7ec87e" roughness={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <planeGeometry args={[pw * 0.95, pd * 0.95]} />
        <meshStandardMaterial color="#c8c8c0" roughness={0.95} />
      </mesh>
    </group>
  );
}

// ─── Trees ────────────────────────────────────────────────────────────────────
function Tree({ position }: { position: [number, number, number] }) {
  const h = 3 + Math.abs(position[0] * 0.3) % 2;
  return (
    <group position={position}>
      <mesh position={[0, h / 4, 0]} castShadow>
        <cylinderGeometry args={[0.12, 0.2, h / 2, 6]} />
        <meshStandardMaterial color="#6b4c2a" roughness={0.9} />
      </mesh>
      {[0.72, 0.58, 0.44].map((yFactor, i) => (
        <mesh key={i} position={[0, h * yFactor, 0]} castShadow>
          <coneGeometry args={[1.3 - i * 0.2, h * (0.6 - i * 0.1), 8]} />
          <meshStandardMaterial color={["#2d7a2d", "#3a8f3a", "#45a045"][i]} roughness={0.85} />
        </mesh>
      ))}
    </group>
  );
}

function Trees() {
  const pw = useStore((s) => s.plotWidth);
  const pd = useStore((s) => s.plotDepth);
  const positions = useMemo<[number, number, number][]>(() => {
    const hw = pw / 2, hd = pd / 2, p = 3;
    return [[-hw - p, 0, -hd - p], [hw + p, 0, -hd - p], [-hw - p, 0, hd + p], [hw + p, 0, hd + p],
      [-hw - p * 2, 0, 0], [hw + p * 2, 0, 0], [0, 0, -hd - p * 2], [0, 0, hd + p * 2]];
  }, [pw, pd]);
  return <>{positions.map((pos, i) => <Tree key={i} position={pos} />)}</>;
}

// ─── Building meshes ──────────────────────────────────────────────────────────
function BuildingMesh({ mesh, materials }: { mesh: any; materials: any[] }) {
  const mat = materials.find((m: any) => (m.id || m.material_id) === mesh.material_id);
  const color = mat?.color_hex || "#c8cdd4";
  const roughness = mat?.roughness ?? 0.8;
  const metalness = mat?.metallic ?? mat?.metalness ?? 0.05;
  const transmission = mat?.transmission ?? 0;
  const opacity = mat?.opacity ?? 1;
  const transparent = !!(mat?.transparent || transmission > 0 || opacity < 1);
  const s = mesh.scale || [1, 1, 1];

  return (
    <mesh position={mesh.position} rotation={mesh.rotation || [0, 0, 0]} castShadow receiveShadow>
      {mesh.type === "prism" || mesh.type === "cone"
        ? <coneGeometry args={[s[0] / 2, s[1], 4]} />
        : <boxGeometry args={s} />}
      {transparent || transmission > 0
        ? <meshPhysicalMaterial color={color} roughness={roughness} metalness={metalness}
            transparent opacity={opacity} transmission={transmission} thickness={0.4} ior={1.45} />
        : <meshStandardMaterial color={color} roughness={roughness} metalness={metalness} />}
    </mesh>
  );
}

function ProceduralScene() {
  const geo = useStore((s) => s.geometryData);
  const manifest = useStore((s) => s.assetManifest);
  const filter = useStore((s) => s.visibleComponentGroup);
  const materials = manifest?.materials || [];
  if (!geo?.meshes?.length) return <EmptyBuilding />;
  const meshes = geo.meshes.filter((m: any) => filter === "All" || m.component_group === filter);
  return (
    <group>
      {meshes.map((m: any) => (
        <MeshBoundary key={m.id}><BuildingMesh mesh={m} materials={materials} /></MeshBoundary>
      ))}
    </group>
  );
}

// ─── Empty placeholder ────────────────────────────────────────────────────────
function EmptyBuilding() {
  const mesh = useRef<THREE.Mesh>(null!);
  useFrame(({ clock }) => {
    if (mesh.current) {
      mesh.current.rotation.y = clock.getElapsedTime() * 0.3;
      mesh.current.position.y = 2 + Math.sin(clock.getElapsedTime() * 0.8) * 0.2;
    }
  });
  return (
    <group>
      <mesh ref={mesh} position={[0, 2, 0]} castShadow>
        <boxGeometry args={[3, 4, 3]} />
        <meshPhysicalMaterial color="#e2e8f0" roughness={0.3} metalness={0.1} wireframe />
      </mesh>
      <Html center position={[0, 5.5, 0]}>
        <div className="text-center pointer-events-none select-none">
          <p className="text-[11px] font-semibold text-slate-500 bg-white/80 backdrop-blur px-3 py-1.5 rounded-full shadow-sm border border-slate-200 whitespace-nowrap">
            Describe your building to get started
          </p>
        </div>
      </Html>
      <mesh position={[0, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[2.5, 3.5, 32]} />
        <meshStandardMaterial color="#7c93c3" transparent opacity={0.15} />
      </mesh>
    </group>
  );
}

// ─── Placed Sketchfab Asset (placeholder box + thumbnail label) ───────────────
function PlacedAssetMesh({ asset, onSelect }: { asset: PlacedAsset; onSelect: (id: string) => void }) {
  const selected = useStore((s) => s.selectedAssetUid) === asset.placement_id;
  const mesh = useRef<THREE.Mesh>(null!);
  const s = asset.scale || 1;

  // Guess bounding box from asset category
  const size: [number, number, number] = [s * 1.2, s * 0.8, s * 1.2];

  return (
    <group
      position={[asset.position.x, asset.position.y, asset.position.z]}
      rotation={[0, asset.rotation?.y || 0, 0]}
      onClick={(e) => { e.stopPropagation(); onSelect(asset.placement_id); }}
    >
      {/* Shadow plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <planeGeometry args={[size[0] * 1.2, size[2] * 1.2]} />
        <meshStandardMaterial color="#000" transparent opacity={0.08} />
      </mesh>
      {/* Placeholder box */}
      <mesh ref={mesh} position={[0, size[1] / 2, 0]} castShadow>
        <boxGeometry args={size} />
        <meshStandardMaterial
          color={selected ? "#7c93c3" : "#e2e8f0"}
          roughness={0.6}
          metalness={0.1}
          transparent opacity={0.85}
        />
      </mesh>
      {/* Selection outline */}
      {selected && (
        <mesh position={[0, size[1] / 2, 0]}>
          <boxGeometry args={[size[0] + 0.05, size[1] + 0.05, size[2] + 0.05]} />
          <meshBasicMaterial color="#7c93c3" wireframe />
        </mesh>
      )}
      {/* Label */}
      <Html position={[0, size[1] + 0.4, 0]} center>
        <div className="pointer-events-none select-none flex flex-col items-center gap-1">
          {asset.thumbnail && (
            <img src={asset.thumbnail} alt={asset.name} draggable={false}
              className="w-10 h-10 rounded-md object-cover shadow-md border-2 border-white" />
          )}
          <span className="text-[9px] font-semibold bg-white/90 text-slate-700 px-2 py-0.5 rounded-full shadow-sm border border-slate-200 whitespace-nowrap max-w-[100px] truncate">
            {asset.name}
          </span>
        </div>
      </Html>
    </group>
  );
}

// ─── Drop overlay (shows while dragging) ──────────────────────────────────────
function DropOverlay({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div className="absolute inset-0 z-20 pointer-events-none border-4 border-dashed border-[#7c93c3]/60 rounded-lg flex items-center justify-center">
      <div className="bg-white/90 backdrop-blur rounded-2xl px-6 py-4 shadow-xl border border-[#7c93c3]/30 flex flex-col items-center gap-2">
        <div className="w-10 h-10 rounded-full bg-[#7c93c3]/15 flex items-center justify-center">
          <svg className="w-5 h-5 text-[#7c93c3]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </div>
        <p className="text-sm font-semibold text-slate-700">Drop to place in scene</p>
        <p className="text-[10px] text-slate-400">Asset will appear on the ground</p>
      </div>
    </div>
  );
}

// ─── Main viewer ──────────────────────────────────────────────────────────────
export default function ThreeJSViewer() {
  const isDrone = useStore((s) => s.isDroneFlying);
  const proj = useStore((s) => s.activeProjection);
  const canOrbit = !isDrone && !proj.startsWith("orthographic") && !proj.startsWith("oblique");
  const placedAssets = useStore((s) => s.placedAssets);
  const addPlacedAsset = useStore((s) => s.addPlacedAsset);
  const setSelectedAssetUid = useStore((s) => s.setSelectedAssetUid);
  const removePlacedAsset = useStore((s) => s.removePlacedAsset);

  const [isDragOver, setIsDragOver] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const assetCounter = useRef(0);

  // Convert 2D screen drop position → approximate 3D world position on Y=0 plane
  const screenTo3D = useCallback((clientX: number, clientY: number): { x: number; y: number; z: number } => {
    const el = containerRef.current;
    if (!el) return { x: 0, y: 0, z: 0 };
    const rect = el.getBoundingClientRect();
    // Normalise to [-1, 1]
    const nx = ((clientX - rect.left) / rect.width) * 2 - 1;
    const nz = ((clientY - rect.top) / rect.height) * 2 - 1;
    // Map to approximate world space (camera at ~18,8,18 looking at 0,3,0)
    // This is a heuristic projection onto y=0 plane
    const spreadX = 12, spreadZ = 10;
    return { x: nx * spreadX, y: 0, z: nz * spreadZ };
  }, []);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    setIsDragOver(true);
  };

  const handleDragLeave = () => setIsDragOver(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    try {
      const data = JSON.parse(e.dataTransfer.getData("application/json"));
      const pos = screenTo3D(e.clientX, e.clientY);
      // Spread assets so they don't stack
      const offset = assetCounter.current * 1.5;
      assetCounter.current++;
      addPlacedAsset({
        placement_id: `placed-${Date.now()}-${data.uid}`,
        uid: data.uid,
        name: data.name,
        thumbnail: data.thumbnail || "",
        position: { x: pos.x + offset * Math.cos(offset), y: 0, z: pos.z + offset * Math.sin(offset) },
        rotation: { x: 0, y: 0, z: 0 },
        scale: 1.0,
        room_context: data.room_context || "exterior",
      });
    } catch (err) {
      console.warn("Drop parse error:", err);
    }
  };

  // Keyboard: Delete selected asset
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.key === "Delete" || e.key === "Backspace") && document.activeElement?.tagName !== "INPUT") {
        const sel = useStore.getState().selectedAssetUid;
        if (sel) { removePlacedAsset(sel); setSelectedAssetUid(null); }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [removePlacedAsset, setSelectedAssetUid]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => setSelectedAssetUid(null)}
    >
      <DropOverlay active={isDragOver} />

      {/* Placed assets count badge */}
      {placedAssets.length > 0 && (
        <div className="absolute bottom-4 left-4 z-10 bg-white/90 backdrop-blur border border-slate-200 rounded-full px-3 py-1 text-[10px] font-medium text-slate-600 shadow-sm flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-[#7c93c3] rounded-full" />
          {placedAssets.length} asset{placedAssets.length !== 1 ? "s" : ""} placed
          <button
            onClick={(e) => { e.stopPropagation(); useStore.getState().clearPlacedAssets(); }}
            className="ml-1 text-slate-400 hover:text-rose-500 transition"
            title="Clear all"
          >×</button>
        </div>
      )}

      <Canvas
        camera={{ position: [18, 8, 18], fov: 60, near: 0.1, far: 1000 }}
        shadows={{ type: THREE.PCFSoftShadowMap }}
        gl={{ antialias: true, alpha: false, preserveDrawingBuffer: true }}
        dpr={[1, 2]}
        style={{ width: "100%", height: "100%" }}
      >
        <React.Suspense fallback={null}>
          <Sky sunPosition={[100, 40, 100]} turbidity={8} rayleigh={0.5} mieCoefficient={0.005} mieDirectionalG={0.8} />
          <color attach="background" args={["#dbeafe"]} />

          <ambientLight intensity={0.55} color="#fff8f0" />
          <directionalLight position={[25, 40, 20]} intensity={1.5} castShadow
            shadow-mapSize={[2048, 2048]} shadow-camera-far={120}
            shadow-camera-left={-30} shadow-camera-right={30}
            shadow-camera-top={30} shadow-camera-bottom={-30}
            shadow-bias={-0.0005} />
          <directionalLight position={[-15, 20, -15]} intensity={0.35} color="#c7d4f5" />
          <hemisphereLight args={["#b9d4f7", "#6aab6a", 0.5]} />
          <Environment preset="dawn" />

          <MeshBoundary><Ground /></MeshBoundary>
          <MeshBoundary><Trees /></MeshBoundary>
          <MeshBoundary><ProceduralScene /></MeshBoundary>

          {/* Placed Sketchfab assets */}
          {placedAssets.map((asset) => (
            <MeshBoundary key={asset.placement_id}>
              <PlacedAssetMesh asset={asset} onSelect={setSelectedAssetUid} />
            </MeshBoundary>
          ))}

          <ContactShadows position={[0, 0.02, 0]} opacity={0.55} scale={60} blur={3} far={12} resolution={512} color="#334155" />

          {canOrbit && (
            <OrbitControls target={[0, 3, 0]} maxPolarAngle={Math.PI / 2 - 0.05}
              minDistance={6} maxDistance={60} enableDamping dampingFactor={0.07} />
          )}
          <CameraController />
        </React.Suspense>
      </Canvas>
    </div>
  );
}
