"use client";

import React, { useEffect, useRef, Component, ErrorInfo, ReactNode, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, ContactShadows, Environment, Sky, useTexture } from "@react-three/drei";
import * as THREE from "three";
import { useStore } from "@/lib/store";

// ─── Error Boundary ───────────────────────────────────────────────────────────

class MeshBoundary extends Component<{children: ReactNode; fallback?: ReactNode}, {err: boolean}> {
  state = { err: false };
  static getDerivedStateFromError() { return { err: true }; }
  componentDidCatch(e: Error) { console.warn("R3F error:", e.message); }
  render() { return this.state.err ? (this.props.fallback ?? null) : this.props.children; }
}

// ─── Camera Controller ────────────────────────────────────────────────────────

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
        const o = new THREE.OrthographicCamera(-fs*asp/2, fs*asp/2, fs/2, -fs/2, 0.1, 500);
        if (proj === "orthographic_top")   { o.position.set(0,40,0.01); o.lookAt(0,0,0); }
        else if (proj === "orthographic_front") { o.position.set(0,6,40); o.lookAt(0,6,0); }
        else if (proj === "orthographic_side")  { o.position.set(40,6,0); o.lookAt(0,6,0); }
        else if (proj === "isometric")      { o.position.set(20,20,20); o.lookAt(0,2,0); }
        else { o.position.set(0,6,30); o.lookAt(0,6,0); }
        camera.position.copy(o.position);
        camera.quaternion.copy(o.quaternion);
        if (camera instanceof THREE.OrthographicCamera) {
          Object.assign(camera, { left:o.left, right:o.right, top:o.top, bottom:o.bottom });
          camera.updateProjectionMatrix();
        }
      } else {
        const pc = camera as THREE.PerspectiveCamera;
        pc.fov = proj === "perspective_1p" ? 42 : proj === "perspective_3p" ? 70 : 60;
        if (proj === "perspective_1p")  { pc.position.set(0,3.5,22); pc.lookAt(0,3.5,0); }
        else if (proj === "perspective_3p") { pc.position.set(20,22,20); pc.lookAt(0,2,0); }
        pc.updateProjectionMatrix();
      }
    } catch(e) { console.warn("cam err:", e); }
  }, [proj, size, camera]);

  useFrame((_, dt) => {
    if (!isDrone || !dronePath?.length) return;
    const cur = dronePath[kf];
    const nxt = dronePath[(kf+1) % dronePath.length];
    progress.current += dt / (cur.duration_s || 4);
    const t = Math.min(progress.current, 1);
    camera.position.lerpVectors(new THREE.Vector3(...cur.position), new THREE.Vector3(...nxt.position), t);
    camera.lookAt(new THREE.Vector3(...(cur.look_at || [0,2,0])));
    if (t >= 1) { progress.current = 0; setKf((kf+1) % dronePath.length); }
  });

  return null;
}

// ─── Ground ───────────────────────────────────────────────────────────────────

function Ground() {
  const pw = useStore((s) => s.plotWidth);
  const pd = useStore((s) => s.plotDepth);
  const r = Math.max(pw, pd) * 0.9;

  return (
    <group>
      {/* Large grass field */}
      <mesh rotation={[-Math.PI/2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
        <circleGeometry args={[r * 3, 64]} />
        <meshStandardMaterial color="#7ec87e" roughness={1} />
      </mesh>
      {/* Plot boundary (paved) */}
      <mesh rotation={[-Math.PI/2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <planeGeometry args={[pw * 0.95, pd * 0.95]} />
        <meshStandardMaterial color="#c8c8c0" roughness={0.95} />
      </mesh>
      {/* Plot edge */}
      <mesh rotation={[-Math.PI/2, 0, 0]} position={[0, 0.005, 0]}>
        <ringGeometry args={[pw * 0.47, pw * 0.48, 48]} />
        <meshStandardMaterial color="#999" roughness={0.9} />
      </mesh>
    </group>
  );
}

// ─── Tree ─────────────────────────────────────────────────────────────────────

function Tree({ position }: { position: [number,number,number] }) {
  const h = 3 + Math.random() * 2;
  return (
    <group position={position}>
      <mesh position={[0, h/4, 0]} castShadow>
        <cylinderGeometry args={[0.12, 0.2, h/2, 6]} />
        <meshStandardMaterial color="#6b4c2a" roughness={0.9} />
      </mesh>
      <mesh position={[0, h * 0.72, 0]} castShadow>
        <coneGeometry args={[0.9, h * 0.6, 8]} />
        <meshStandardMaterial color="#2d7a2d" roughness={0.85} />
      </mesh>
      <mesh position={[0, h * 0.58, 0]} castShadow>
        <coneGeometry args={[1.1, h * 0.5, 8]} />
        <meshStandardMaterial color="#3a8f3a" roughness={0.85} />
      </mesh>
      <mesh position={[0, h * 0.44, 0]} castShadow>
        <coneGeometry args={[1.3, h * 0.4, 8]} />
        <meshStandardMaterial color="#45a045" roughness={0.85} />
      </mesh>
    </group>
  );
}

function Trees() {
  const pw = useStore((s) => s.plotWidth);
  const pd = useStore((s) => s.plotDepth);
  const trees: [number,number,number][] = useMemo(() => {
    const hw = pw / 2, hd = pd / 2;
    const pad = 3;
    return [
      [-(hw + pad), 0, -(hd + pad)],
      [hw + pad, 0, -(hd + pad)],
      [-(hw + pad), 0, hd + pad],
      [hw + pad, 0, hd + pad],
      [-(hw + pad * 2), 0, 0],
      [hw + pad * 2, 0, 0],
      [0, 0, -(hd + pad * 2)],
      [0, 0, hd + pad * 2],
    ];
  }, [pw, pd]);

  return (
    <>
      {trees.map((pos, i) => <Tree key={i} position={pos} />)}
    </>
  );
}

// ─── Building Mesh ────────────────────────────────────────────────────────────

function BuildingMesh({ mesh, materials }: { mesh: any; materials: any[] }) {
  const mat = materials.find((m: any) => (m.id || m.material_id) === mesh.material_id);
  const color = mat?.color_hex || mat?.color || "#c8cdd4";
  const roughness = mat?.roughness ?? 0.8;
  const metalness = mat?.metallic ?? mat?.metalness ?? 0.05;
  const transmission = mat?.transmission ?? 0;
  const opacity = mat?.opacity ?? 1;
  const transparent = !!(mat?.transparent || transmission > 0 || opacity < 1);

  let geom: ReactNode;
  const s = mesh.scale || [1,1,1];
  if (mesh.type === "prism" || mesh.type === "cone") {
    geom = <coneGeometry args={[s[0]/2, s[1], 4]} />;
  } else if (mesh.type === "cylinder") {
    geom = <cylinderGeometry args={[s[0]/2, s[0]/2, s[1], 16]} />;
  } else {
    geom = <boxGeometry args={s} />;
  }

  return (
    <mesh position={mesh.position} rotation={mesh.rotation || [0,0,0]} castShadow receiveShadow>
      {geom}
      {transparent || transmission > 0 ? (
        <meshPhysicalMaterial
          color={color} roughness={roughness} metalness={metalness}
          transparent opacity={opacity} transmission={transmission}
          thickness={0.4} ior={1.45} envMapIntensity={1.2}
        />
      ) : (
        <meshStandardMaterial color={color} roughness={roughness} metalness={metalness} />
      )}
    </mesh>
  );
}

// ─── Empty State Placeholder ──────────────────────────────────────────────────

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
      <mesh position={[0, 0.01, 0]} rotation={[-Math.PI/2,0,0]}>
        <ringGeometry args={[2.5, 3.5, 32]} />
        <meshStandardMaterial color="#7c93c3" transparent opacity={0.15} />
      </mesh>
    </group>
  );
}

// ─── Scene ────────────────────────────────────────────────────────────────────

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
        <MeshBoundary key={m.id}>
          <BuildingMesh mesh={m} materials={materials} />
        </MeshBoundary>
      ))}
    </group>
  );
}

// ─── Main Viewer ──────────────────────────────────────────────────────────────

export default function ThreeJSViewer() {
  const isDrone = useStore((s) => s.isDroneFlying);
  const proj = useStore((s) => s.activeProjection);
  const canOrbit = !isDrone && !proj.startsWith("orthographic") && !proj.startsWith("oblique");

  return (
    <div className="relative w-full h-full">
      <Canvas
        camera={{ position: [18, 8, 18], fov: 60, near: 0.1, far: 1000 }}
        shadows={{ type: THREE.PCFSoftShadowMap }}
        gl={{ antialias: true, alpha: false, preserveDrawingBuffer: true }}
        dpr={[1, 2]}
      >
        <React.Suspense fallback={null}>
          {/* Sky */}
          <Sky sunPosition={[100, 40, 100]} turbidity={8} rayleigh={0.5} mieCoefficient={0.005} mieDirectionalG={0.8} />
          <color attach="background" args={["#dbeafe"]} />

          {/* Lighting */}
          <ambientLight intensity={0.55} color="#fff8f0" />
          <directionalLight
            position={[25, 40, 20]} intensity={1.5} castShadow
            shadow-mapSize={[2048, 2048]} shadow-camera-far={120}
            shadow-camera-left={-30} shadow-camera-right={30}
            shadow-camera-top={30} shadow-camera-bottom={-30}
            shadow-bias={-0.0005}
          />
          <directionalLight position={[-15, 20, -15]} intensity={0.35} color="#c7d4f5" />
          <hemisphereLight args={["#b9d4f7","#6aab6a", 0.5]} />

          {/* Environment for reflections */}
          <Environment preset="dawn" />

          {/* Scene objects */}
          <MeshBoundary><Ground /></MeshBoundary>
          <MeshBoundary><Trees /></MeshBoundary>
          <MeshBoundary><ProceduralScene /></MeshBoundary>

          {/* Soft shadow on ground */}
          <ContactShadows
            position={[0, 0.02, 0]} opacity={0.55} scale={60}
            blur={3} far={12} resolution={512} color="#334155"
          />

          {/* Controls */}
          {canOrbit && (
            <OrbitControls
              target={[0, 3, 0]}
              maxPolarAngle={Math.PI / 2 - 0.05}
              minDistance={6} maxDistance={60}
              enableDamping dampingFactor={0.07}
              autoRotate={false}
            />
          )}
          <CameraController />
        </React.Suspense>
      </Canvas>
    </div>
  );
}
