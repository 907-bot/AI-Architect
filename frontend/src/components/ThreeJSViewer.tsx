"use client";

import React, {
  useEffect, useRef, Component, ErrorInfo, ReactNode,
  useMemo, useState, useCallback,
} from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  OrbitControls, ContactShadows, Sky, Html, useGLTF,
  OrthographicCamera,
} from "@react-three/drei";
import * as THREE from "three";
import { useStore, PlacedAsset } from "@/lib/store";
import { API_BASE } from "@/lib/mvpScene";

// ─── Error Boundary ───────────────────────────────────────────────────────────
class MeshBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  { err: boolean }
> {
  state = { err: false };
  static getDerivedStateFromError() { return { err: true }; }
  componentDidCatch(e: Error) { console.warn("R3F error:", e.message); }
  render() {
    return this.state.err
      ? (this.props.fallback ?? null)
      : this.props.children;
  }
}

// ─── Camera + OrbitControls controller ───────────────────────────────────────
// Single component owns BOTH camera movement and OrbitControls to avoid conflicts.
function CameraRig({ orbitRef }: { orbitRef: React.MutableRefObject<any> }) {
  const { camera } = useThree();
  const proj      = useStore((s) => s.activeProjection);
  const isDrone   = useStore((s) => s.isDroneFlying);
  const dronePath = useStore((s) => s.dronePath);
  const kf        = useStore((s) => s.currentDroneKeyframe);
  const setKf     = useStore((s) => s.setDroneKeyframe);
  const progress  = useRef(0);
  const prevProj  = useRef(proj);

  // Move camera when projection changes
  useEffect(() => {
    if (prevProj.current === proj) return;
    prevProj.current = proj;

    try {
      // Disable orbit while we reposition
      if (orbitRef.current) orbitRef.current.enabled = false;

      if (proj === "orthographic_top") {
        camera.position.set(0, 60, 0.01); camera.lookAt(0, 0, 0);
      } else if (proj === "orthographic_front") {
        camera.position.set(0, 8, 55); camera.lookAt(0, 8, 0);
      } else if (proj === "orthographic_side") {
        camera.position.set(55, 8, 0); camera.lookAt(0, 8, 0);
      } else if (proj === "isometric") {
        camera.position.set(28, 28, 28); camera.lookAt(0, 4, 0);
      } else if (proj === "perspective_1p") {
        (camera as THREE.PerspectiveCamera).fov = 42;
        camera.position.set(0, 5, 28); camera.lookAt(0, 5, 0);
      } else if (proj === "perspective_3p") {
        (camera as THREE.PerspectiveCamera).fov = 70;
        camera.position.set(22, 24, 22); camera.lookAt(0, 4, 0);
      } else {
        // Default perspective_2p
        (camera as THREE.PerspectiveCamera).fov = 55;
        camera.position.set(22, 14, 22); camera.lookAt(0, 4, 0);
      }
      (camera as THREE.PerspectiveCamera).updateProjectionMatrix?.();

      // Re-enable orbit and sync its target
      if (orbitRef.current) {
        orbitRef.current.target.set(0, 4, 0);
        orbitRef.current.update();
        // Re-enable after a short delay so the camera snap completes
        setTimeout(() => {
          if (orbitRef.current) orbitRef.current.enabled = true;
        }, 80);
      }
    } catch (e) { console.warn("cam err:", e); }
  }, [proj, camera, orbitRef]);

  // Drone flythrough
  useFrame((_, dt) => {
    if (!isDrone || !dronePath?.length) return;
    const cur = dronePath[kf];
    const nxt = dronePath[(kf + 1) % dronePath.length];
    progress.current += dt / (cur.duration_s || 4);
    const t = Math.min(progress.current, 1);
    camera.position.lerpVectors(
      new THREE.Vector3(...cur.position),
      new THREE.Vector3(...nxt.position), t);
    camera.lookAt(new THREE.Vector3(...(cur.look_at || [0, 4, 0])));
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
        <circleGeometry args={[Math.max(pw, pd) * 3.5, 64]} />
        <meshStandardMaterial color="#5a9e5a" roughness={1} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <planeGeometry args={[pw * 1.1, pd * 1.1]} />
        <meshStandardMaterial color="#b0afa8" roughness={0.95} />
      </mesh>
    </group>
  );
}

// ─── Trees (away from pool/garage zones) ─────────────────────────────────────
function Tree({ position }: { position: [number, number, number] }) {
  const h = 3.5 + Math.abs(position[0] * 0.3) % 2.5;
  const colors = ["#2d6e2d", "#3a8a3a", "#1e5c1e"];
  return (
    <group position={position}>
      <mesh position={[0, h * 0.15, 0]} castShadow>
        <cylinderGeometry args={[0.14, 0.22, h * 0.3, 7]} />
        <meshStandardMaterial color="#5c3d1e" roughness={0.9} />
      </mesh>
      {[0.65, 0.52, 0.40].map((yf, i) => (
        <mesh key={i} position={[0, h * yf, 0]} castShadow>
          <coneGeometry args={[1.5 - i * 0.3, h * (0.55 - i * 0.08), 9]} />
          <meshStandardMaterial color={colors[i]} roughness={0.85} />
        </mesh>
      ))}
    </group>
  );
}

function Trees() {
  const pw = useStore((s) => s.plotWidth);
  const pd = useStore((s) => s.plotDepth);
  // Keep trees away from: pool (right/front), garage (left/front), lobby (front-center)
  const positions = useMemo<[number, number, number][]>(() => {
    const hw = pw / 2, hd = pd / 2;
    return [
      [-hw - 5,  hd + 6,  0],   // back-left
      [ hw + 5,  hd + 6,  0],   // back-right
      [0,        hd + 7,  0],   // back-centre
      [-hw - 6,  hd / 2,  0],   // mid-left
      [ hw + 6,  hd,      0],   // mid-right-back (clear of pool)
      [-hw - 9, -hd - 6,  0],   // far front-left (beyond garage)
      [ hw + 9, -hd - 6,  0],   // far front-right (beyond pool)
      [-hw - 4,  hd + 2,  0],   // back-left cluster
    ];
  }, [pw, pd]);
  return <>{positions.map((pos, i) => <Tree key={i} position={pos} />)}</>;
}

// ─── GLB component filter ─────────────────────────────────────────────────────
const COMPONENT_PREFIXES: Record<string, string[]> = {
  "All":        [],  // empty = show all
  "Foundation": ["Foundation", "Plinth", "BasePad", "Ground"],
  "Floor Slabs":["Slab_", "SlabEdge_"],
  "Walls":      ["Wall_", "Lobby_Wall"],
  "Windows":    ["Win_", "Lobby_Glass"],
  "Doors":      ["Lobby_Door", "GDoor", "Garage_Door"],
  "Roof":       ["Roof_", "Par_", "Cap_"],
  "Interior":   ["Stair", "Lobby"],
};

function FilteredGLB({ path, filter }: { path: string; filter: string }) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const { scene } = useGLTF(url);
  const groupRef = useRef<THREE.Group>(null!);
  const cloned   = useMemo(() => scene.clone(), [scene]);

  // Auto-fit on load
  useEffect(() => {
    if (!groupRef.current) return;
    const box = new THREE.Box3().setFromObject(groupRef.current);
    const sz  = box.getSize(new THREE.Vector3());
    const maxD = Math.max(sz.x, sz.y, sz.z);
    const s   = maxD > 0 ? 18 / maxD : 1;
    groupRef.current.scale.setScalar(s);
    const nb = new THREE.Box3().setFromObject(groupRef.current);
    groupRef.current.position.y = -nb.min.y;
    groupRef.current.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        child.castShadow    = true;
        child.receiveShadow = true;
      }
    });
  }, [path]);

  // Apply component filter by object name
  useEffect(() => {
    if (!groupRef.current) return;
    const prefixes = COMPONENT_PREFIXES[filter] ?? [];
    groupRef.current.traverse((child) => {
      if (!(child as THREE.Mesh).isMesh) return;
      if (prefixes.length === 0) {
        child.visible = true;
        return;
      }
      const name = child.name || child.parent?.name || "";
      child.visible = prefixes.some((p) => name.startsWith(p));
    });
  }, [filter]);

  return (
    <group key={path}>
      <primitive ref={groupRef} object={cloned} />
    </group>
  );
}

// ─── Procedural scene (fallback when no GLB) ─────────────────────────────────
function BuildingMesh({ mesh, materials }: { mesh: any; materials: any[] }) {
  const mat = materials.find((m: any) =>
    (m.id || m.material_id) === mesh.material_id);
  const color       = mat?.color_hex  ?? "#c8cdd4";
  const roughness   = mat?.roughness  ?? 0.8;
  const metalness   = mat?.metallic   ?? mat?.metalness ?? 0.05;
  const transmission = mat?.transmission ?? 0;
  const opacity     = mat?.opacity    ?? 1;
  const transparent = !!(mat?.transparent || transmission > 0 || opacity < 1);
  const s = mesh.scale || [1, 1, 1];

  return (
    <mesh position={mesh.position} rotation={mesh.rotation || [0, 0, 0]}
      castShadow receiveShadow>
      <boxGeometry args={s} />
      {transparent || transmission > 0
        ? <meshPhysicalMaterial color={color} roughness={roughness}
            metalness={metalness} transparent opacity={opacity}
            transmission={transmission} thickness={0.4} ior={1.45} />
        : <meshStandardMaterial color={color} roughness={roughness}
            metalness={metalness} />}
    </mesh>
  );
}

function ProceduralScene() {
  const geo      = useStore((s) => s.geometryData);
  const manifest = useStore((s) => s.assetManifest);
  const filter   = useStore((s) => s.visibleComponentGroup);
  const materials = manifest?.materials || [];
  if (!geo?.meshes?.length) return <EmptyBuilding />;
  const meshes = geo.meshes.filter(
    (m: any) => filter === "All" || m.component_group === filter);
  return (
    <group>
      {meshes.map((m: any) => (
        <MeshBoundary key={m.id}><BuildingMesh mesh={m} materials={materials} /></MeshBoundary>
      ))}
      {filter === "All" && (geo.rooms || []).map((room: any) => (
        <Html key={room.id || room.name} center
          position={[room.x, 3.85, room.y || 0]}>
          <div className="pointer-events-none select-none rounded-full border border-slate-200 bg-white/90 px-2.5 py-1 text-[10px] font-semibold text-slate-700 shadow-sm whitespace-nowrap">
            {(room.name || room.id || "room").replaceAll("_", " ")}
          </div>
        </Html>
      ))}
    </group>
  );
}

// ─── Empty placeholder ────────────────────────────────────────────────────────
function EmptyBuilding() {
  const mesh = useRef<THREE.Mesh>(null!);
  useFrame(({ clock }) => {
    if (mesh.current) {
      mesh.current.rotation.y  = clock.getElapsedTime() * 0.3;
      mesh.current.position.y  = 2 + Math.sin(clock.getElapsedTime() * 0.8) * 0.2;
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
    </group>
  );
}

// ─── Placed asset ─────────────────────────────────────────────────────────────
function SketchfabGLB({ url, scale }: { url: string; scale: number }) {
  const { scene } = useGLTF(url);
  const ref = useRef<THREE.Group>(null!);
  useEffect(() => {
    if (!ref.current) return;
    const box  = new THREE.Box3().setFromObject(ref.current);
    const size = box.getSize(new THREE.Vector3());
    const maxD = Math.max(size.x, size.y, size.z);
    const s    = maxD > 0 ? scale / maxD : scale;
    ref.current.scale.setScalar(s);
    const nb = new THREE.Box3().setFromObject(ref.current);
    ref.current.position.y = -nb.min.y;
    ref.current.traverse((c) => {
      if ((c as THREE.Mesh).isMesh) { c.castShadow = true; c.receiveShadow = true; }
    });
  }, [url, scale]);
  return <primitive ref={ref} object={scene.clone()} />;
}

function LocalAssetFallback({ asset, size }: { asset: PlacedAsset; size: [number,number,number] }) {
  const name = (asset.name || "").toLowerCase();
  if (name.includes("tree") || name.includes("plant")) {
    return (
      <group>
        <mesh position={[0, 0.55, 0]} castShadow>
          <cylinderGeometry args={[0.12, 0.18, 1.1, 8]} />
          <meshStandardMaterial color="#8b5a2b" roughness={0.8} />
        </mesh>
        <mesh position={[0, 1.35, 0]} castShadow>
          <coneGeometry args={[0.8, 1.5, 10]} />
          <meshStandardMaterial color="#3f8f46" roughness={0.85} />
        </mesh>
      </group>
    );
  }
  return (
    <mesh position={[0, size[1] / 2, 0]} castShadow>
      <boxGeometry args={size} />
      <meshStandardMaterial color="#94a3b8" roughness={0.6} />
    </mesh>
  );
}

function PlacedAssetMesh({ asset, onSelect }: { asset: PlacedAsset; onSelect: (id: string) => void }) {
  const selected = useStore((s) => s.selectedAssetUid) === asset.placement_id;
  const s = asset.scale || 1;
  const size: [number, number, number] = [s * 1.2, s * 0.8, s * 1.2];
  const glbUrl = (() => {
    if (asset.local_path) {
      const fn = asset.local_path.split(/[/\\]/).pop();
      return `${API_BASE}/cache/sketchfab/${fn}`;
    }
    if (asset.glb_url && !asset.glb_url.includes("stub://")) return asset.glb_url;
    return "";
  })();
  const pos: [number,number,number] = Array.isArray(asset.position)
    ? asset.position as [number,number,number]
    : [asset.position.x, asset.position.y, asset.position.z];
  const rot: [number,number,number] = [0, (asset.rotation as any)?.y || 0, 0];

  return (
    <group position={pos} rotation={rot}
      onClick={(e) => { e.stopPropagation(); onSelect(asset.placement_id); }}>
      {glbUrl ? (
        <React.Suspense fallback={
          <mesh position={[0, size[1]/2, 0]} castShadow>
            <boxGeometry args={size} />
            <meshStandardMaterial color="#94a3b8" roughness={0.6} />
          </mesh>}>
          <MeshBoundary fallback={<LocalAssetFallback asset={asset} size={size} />}>
            <SketchfabGLB url={glbUrl} scale={s * 2} />
          </MeshBoundary>
        </React.Suspense>
      ) : (
        <LocalAssetFallback asset={asset} size={size} />
      )}
      {selected && (
        <mesh position={[0, size[1]/2, 0]}>
          <boxGeometry args={[size[0]+0.1, size[1]+0.1, size[2]+0.1]} />
          <meshBasicMaterial color="#7c93c3" wireframe />
        </mesh>
      )}
      <Html position={[0, size[1]+0.5, 0]} center>
        <div className="pointer-events-none select-none">
          <span className="text-[9px] font-semibold bg-white/90 text-slate-700 px-2 py-0.5 rounded-full shadow-sm border border-slate-200 whitespace-nowrap max-w-[100px] truncate">
            {asset.name}
          </span>
        </div>
      </Html>
    </group>
  );
}

// ─── Drop overlay ─────────────────────────────────────────────────────────────
function DropOverlay({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div className="absolute inset-0 z-20 pointer-events-none border-4 border-dashed border-[#7c93c3]/60 rounded-lg flex items-center justify-center">
      <div className="bg-white/90 backdrop-blur rounded-2xl px-6 py-4 shadow-xl border border-[#7c93c3]/30 flex flex-col items-center gap-2">
        <p className="text-sm font-semibold text-slate-700">Drop to place in scene</p>
      </div>
    </div>
  );
}

// ─── Main viewer ──────────────────────────────────────────────────────────────
export default function ThreeJSViewer() {
  const isDrone       = useStore((s) => s.isDroneFlying);
  const proj          = useStore((s) => s.activeProjection);
  const placedAssets  = useStore((s) => s.placedAssets);
  const addPlacedAsset    = useStore((s) => s.addPlacedAsset);
  const updatePlacedAsset = useStore((s) => s.updatePlacedAsset);
  const setSelectedAssetUid = useStore((s) => s.setSelectedAssetUid);
  const removePlacedAsset   = useStore((s) => s.removePlacedAsset);
  const generatedGlbPath    = useStore((s) => s.generatedGlbPath);
  const filter        = useStore((s) => s.visibleComponentGroup);

  const [isDragOver, setIsDragOver] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const orbitRef     = useRef<any>(null);
  const assetCounter = useRef(0);

  const isOrtho = proj.startsWith("orthographic") || proj === "isometric" || proj.startsWith("oblique");
  // Orbit is always enabled for perspective views — drone disables it
  const canOrbit = !isDrone;

  const screenTo3D = useCallback((clientX: number, clientY: number) => {
    const el = containerRef.current;
    if (!el) return { x: 0, y: 0, z: 0 };
    const rect = el.getBoundingClientRect();
    const nx = ((clientX - rect.left) / rect.width) * 2 - 1;
    const nz = ((clientY - rect.top) / rect.height) * 2 - 1;
    return { x: nx * 12, y: 0, z: nz * 10 };
  }, []);

  const handleDragOver  = (e: React.DragEvent) => {
    e.preventDefault(); e.dataTransfer.dropEffect = "copy"; setIsDragOver(true);
  };
  const handleDragLeave = () => setIsDragOver(false);

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    let data: any;
    try {
      const raw = e.dataTransfer.getData("application/json") || e.dataTransfer.getData("text/plain");
      if (!raw) return;
      data = JSON.parse(raw);
    } catch { return; }

    const pos = screenTo3D(e.clientX, e.clientY);
    const offset = assetCounter.current * 1.8;
    assetCounter.current++;
    const placementId = `placed-${Date.now()}-${data.uid}`;

    addPlacedAsset({
      placement_id: placementId, asset_uid: data.uid, name: data.name,
      thumbnail: data.thumbnail || "",
      position: [pos.x + offset * Math.cos(offset), 0, pos.z + offset * Math.sin(offset)],
      rotation: [0, 0, 0], scale: 1.5, glb_url: undefined, local_path: undefined,
    });

    try {
      const resp = await fetch(`${API_BASE}/api/sketchfab/drag-drop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          asset_uid: data.uid, drop_position: { x: pos.x, y: 0, z: pos.z },
          surface_normal: { x: 0, y: 1, z: 0 },
          room_context: data.room_context || "interior",
          auto_orient: true, auto_scale: true,
        }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const placement = await resp.json();
      updatePlacedAsset(placementId, {
        glb_url: placement.glb_url || undefined,
        local_path: placement.local_path || undefined,
        scale: placement.scale || 1.5,
        rotation: [placement.rotation?.x||0, placement.rotation?.y||0, placement.rotation?.z||0],
      });
    } catch (err) { console.error("GLB fetch failed:", err); }
  };

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
    <div ref={containerRef} className="absolute inset-0"
      onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}
      onClick={() => setSelectedAssetUid(null)}>
      <DropOverlay active={isDragOver} />

      {generatedGlbPath && (
        <div className="absolute bottom-4 right-4 z-10 rounded-full border border-emerald-200 bg-white/90 px-3 py-1.5 text-[10px] font-semibold text-emerald-700 shadow-lg backdrop-blur flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Blender GLB
          <span className="font-mono text-emerald-600/80">{generatedGlbPath.split("/").pop()}</span>
        </div>
      )}

      {placedAssets.length > 0 && (
        <div className="absolute bottom-4 left-4 z-10 bg-white/90 backdrop-blur border border-slate-200 rounded-full px-3 py-1 text-[10px] font-medium text-slate-600 shadow-sm flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-[#7c93c3] rounded-full" />
          {placedAssets.length} asset{placedAssets.length !== 1 ? "s" : ""} placed
          <button onClick={(e) => { e.stopPropagation(); useStore.getState().clearPlacedAssets(); }}
            className="ml-1 text-slate-400 hover:text-rose-500 transition">×</button>
        </div>
      )}

      <Canvas
        camera={{ position: [22, 14, 22], fov: 55, near: 0.1, far: 1500 }}
        shadows={{ type: THREE.PCFSoftShadowMap }}
        gl={{ antialias: true, alpha: false, preserveDrawingBuffer: true }}
        dpr={[1, 2]}
        style={{ width: "100%", height: "100%" }}
      >
        <React.Suspense fallback={null}>
          <Sky sunPosition={[80, 35, 60]} turbidity={6} rayleigh={0.5}
            mieCoefficient={0.005} mieDirectionalG={0.8} />
          <color attach="background" args={["#d6eaf8"]} />

          <ambientLight intensity={0.6} color="#fff8f0" />
          <directionalLight position={[30, 45, 25]} intensity={1.8} castShadow
            shadow-mapSize={[2048, 2048]} shadow-camera-far={150}
            shadow-camera-left={-40} shadow-camera-right={40}
            shadow-camera-top={40} shadow-camera-bottom={-40}
            shadow-bias={-0.0005} />
          <directionalLight position={[-20, 25, -20]} intensity={0.4} color="#c7d4f5" />
          <hemisphereLight args={["#b9d4f7", "#6aab6a", 0.5]} />

          {/* Orthographic camera for top/front/side views */}
          {isOrtho && proj === "orthographic_top" && (
            <OrthographicCamera makeDefault position={[0, 60, 0.01]} zoom={40} near={0.1} far={300} />
          )}

          <MeshBoundary><Ground /></MeshBoundary>
          <MeshBoundary><Trees /></MeshBoundary>

          {/* Main building — GLB with filter, or procedural fallback */}
          {generatedGlbPath ? (
            <MeshBoundary fallback={<ProceduralScene />}>
              <FilteredGLB path={generatedGlbPath} filter={filter} />
            </MeshBoundary>
          ) : (
            <MeshBoundary><ProceduralScene /></MeshBoundary>
          )}

          {placedAssets.map((asset) => (
            <MeshBoundary key={asset.placement_id}>
              <PlacedAssetMesh asset={asset} onSelect={setSelectedAssetUid} />
            </MeshBoundary>
          ))}

          <ContactShadows position={[0, 0.02, 0]} opacity={0.5} scale={70}
            blur={3} far={14} resolution={512} color="#334155" />

          {/* OrbitControls — always present, CameraRig enables/disables */}
          {canOrbit && (
            <OrbitControls
              ref={orbitRef}
              target={[0, 4, 0]}
              maxPolarAngle={Math.PI / 1.9}   // allow slight below-horizon
              minPolarAngle={0.05}
              minDistance={5}
              maxDistance={120}
              enableDamping
              dampingFactor={0.06}
              enablePan={true}
              panSpeed={0.8}
              rotateSpeed={0.7}
              zoomSpeed={1.2}
            />
          )}
          <CameraRig orbitRef={orbitRef} />
          <WalkthroughController />
        </React.Suspense>
      </Canvas>
    </div>
  );
}

// ─── First-Person Walkthrough ─────────────────────────────────────────────────
// Exported so page.tsx can show the Enter/Exit button
export function WalkthroughController() {
  const { camera, gl } = useThree();
  const isWalk   = useStore((s) => s.isWalkthrough);
  const setWalk  = useStore((s) => s.setWalkthrough);
  const keys     = useRef<Set<string>>(new Set());
  const locked   = useRef(false);
  const yaw      = useRef(0);
  const pitch    = useRef(0);

  // Pointer lock
  useEffect(() => {
    if (!isWalk) return;
    const canvas = gl.domElement;
    const onLock = () => { locked.current = true; };
    const onUnlock = () => { locked.current = false; setWalk(false); };
    const onMove = (e: MouseEvent) => {
      if (!locked.current) return;
      yaw.current   -= e.movementX * 0.002;
      pitch.current -= e.movementY * 0.002;
      pitch.current  = Math.max(-1.2, Math.min(1.2, pitch.current));
    };
    document.addEventListener("pointerlockchange", onLock);
    document.addEventListener("pointerlockerror",  onUnlock);
    document.addEventListener("mousemove", onMove);
    canvas.requestPointerLock();
    return () => {
      document.removeEventListener("pointerlockchange", onLock);
      document.removeEventListener("pointerlockerror",  onUnlock);
      document.removeEventListener("mousemove", onMove);
      if (document.pointerLockElement) document.exitPointerLock();
    };
  }, [isWalk, gl, setWalk]);

  // Keyboard
  useEffect(() => {
    if (!isWalk) return;
    const dn = (e: KeyboardEvent) => { keys.current.add(e.code); };
    const up = (e: KeyboardEvent) => { keys.current.delete(e.code); if (e.code === "Escape") setWalk(false); };
    window.addEventListener("keydown", dn);
    window.addEventListener("keyup",   up);
    return () => { window.removeEventListener("keydown", dn); window.removeEventListener("keyup", up); };
  }, [isWalk, setWalk]);

  // Enter walkthrough — position camera inside building
  useEffect(() => {
    if (isWalk) {
      camera.position.set(0, 1.7, 6);
      yaw.current   = 0;
      pitch.current = 0;
    }
  }, [isWalk, camera]);

  useFrame((_, dt) => {
    if (!isWalk) return;
    const speed = keys.current.has("ShiftLeft") ? 6 : 3;
    const dir   = new THREE.Vector3(0, 0, -1);
    dir.applyEuler(new THREE.Euler(0, yaw.current, 0));

    if (keys.current.has("KeyW") || keys.current.has("ArrowUp"))
      camera.position.addScaledVector(dir, speed * dt);
    if (keys.current.has("KeyS") || keys.current.has("ArrowDown"))
      camera.position.addScaledVector(dir, -speed * dt);
    if (keys.current.has("KeyA") || keys.current.has("ArrowLeft")) {
      const left = dir.clone().cross(new THREE.Vector3(0, 1, 0)).negate();
      camera.position.addScaledVector(left, speed * dt);
    }
    if (keys.current.has("KeyD") || keys.current.has("ArrowRight")) {
      const right = dir.clone().cross(new THREE.Vector3(0, 1, 0));
      camera.position.addScaledVector(right, speed * dt);
    }

    // Apply look rotation
    camera.rotation.order = "YXZ";
    camera.rotation.y     = yaw.current;
    camera.rotation.x     = pitch.current;
    // Keep feet on ground (rough clamp)
    if (camera.position.y < 1.6) camera.position.y = 1.6;
  });

  return null;
}
