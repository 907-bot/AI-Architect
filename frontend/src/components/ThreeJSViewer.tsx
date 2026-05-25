"use client";

import React, { useEffect, useRef, Component, ErrorInfo, ReactNode } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Grid, ContactShadows, Environment, Center } from "@react-three/drei";
import * as THREE from "three";
import { useStore, ProjectionType, ComponentGroupFilter } from "@/lib/store";

// Generic error boundary to isolate component failures
interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}
interface ErrorBoundaryState {
  hasError: boolean;
}
class MeshErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.warn("Three.js component error:", error.message, info.componentStack);
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback || null;
    }
    return this.props.children;
  }
}

// Camera Controller to update camera projection matrices dynamically
function ProjectionCameraController() {
  const { camera, size } = useThree();
  const activeProjection = useStore((state) => state.activeProjection);
  const dronePath = useStore((state) => state.dronePath);
  const isDroneFlying = useStore((state) => state.isDroneFlying);
  const currentKeyframe = useStore((state) => state.currentDroneKeyframe);
  const setDroneKeyframe = useStore((state) => state.setDroneKeyframe);
  const progressRef = useRef(0);

  useEffect(() => {
    try {
      if (activeProjection.startsWith("orthographic") || activeProjection === "isometric" || activeProjection.startsWith("oblique")) {
        const aspect = size.width / size.height;
        const frustumSize = 25;
        const orthoCam = new THREE.OrthographicCamera(
          frustumSize * aspect / -2, frustumSize * aspect / 2,
          frustumSize / 2, frustumSize / -2, 0.1, 1000
        );
        if (activeProjection === "orthographic_top") {
          orthoCam.position.set(0, 30, 0); orthoCam.lookAt(0, 0, 0);
        } else if (activeProjection === "orthographic_front") {
          orthoCam.position.set(0, 5, 30); orthoCam.lookAt(0, 5, 0);
        } else if (activeProjection === "orthographic_side") {
          orthoCam.position.set(30, 5, 0); orthoCam.lookAt(0, 5, 0);
        } else if (activeProjection === "isometric") {
          const val = 15;
          orthoCam.position.set(val, val, val); orthoCam.lookAt(0, 1.5, 0);
        } else if (activeProjection === "oblique_cavalier" || activeProjection === "oblique_cabinet") {
          const val = 18;
          const scaleFactor = activeProjection === "oblique_cabinet" ? 0.5 : 1.0;
          orthoCam.position.set(0, 5, val); orthoCam.lookAt(0, 5, 0);
          const alpha = Math.PI / 6;
          const matrix = new THREE.Matrix4();
          matrix.set(1, 0, -scaleFactor * Math.cos(alpha), 0, 0, 1, -scaleFactor * Math.sin(alpha), 0, 0, 0, 1, 0, 0, 0, 0, 1);
          orthoCam.projectionMatrix.multiply(matrix);
        }
        camera.position.copy(orthoCam.position);
        camera.rotation.copy(orthoCam.rotation);
        if (camera instanceof THREE.OrthographicCamera) {
          camera.left = frustumSize * aspect / -2;
          camera.right = frustumSize * aspect / 2;
          camera.top = frustumSize / 2;
          camera.bottom = frustumSize / -2;
          camera.projectionMatrix.copy(orthoCam.projectionMatrix);
        } else {
          Object.setPrototypeOf(camera, THREE.OrthographicCamera.prototype);
          Object.assign(camera, orthoCam);
        }
        camera.updateProjectionMatrix();
      } else {
        Object.setPrototypeOf(camera, THREE.PerspectiveCamera.prototype);
        const persCam = camera as THREE.PerspectiveCamera;
        persCam.fov = activeProjection === "perspective_1p" ? 40 : 60;
        if (activeProjection === "perspective_1p") {
          persCam.position.set(0, 2.5, 18); persCam.lookAt(0, 2.5, 0);
        } else if (activeProjection === "perspective_3p") {
          persCam.position.set(18, 20, 18); persCam.lookAt(0, 1.5, 0);
        } else if (activeProjection === "perspective_2p" && !isDroneFlying) {
          persCam.position.set(15, 12, 15); persCam.lookAt(0, 1.5, 0);
        }
        persCam.updateProjectionMatrix();
      }
    } catch (e) {
      console.warn("Camera controller error:", e);
    }
  }, [activeProjection, size, camera]);

  useFrame((state, delta) => {
    if (!isDroneFlying || !dronePath || dronePath.length === 0) return;
    try {
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
    } catch (e) {
      console.warn("Drone frame error:", e);
    }
  });

  return null;
}

function PlotLand() {
  const plotWidth = useStore((state) => state.plotWidth);
  const plotDepth = useStore((state) => state.plotDepth);
  const radius = Math.max(plotWidth || 20, plotDepth || 30) * 0.7;

  return (
    <MeshErrorBoundary>
      <group position={[0, -0.25, 0]}>
        <mesh receiveShadow>
          <cylinderGeometry args={[radius, radius * 0.9, 0.5, 64]} />
          <meshStandardMaterial color="#d4d4d8" roughness={0.8} />
        </mesh>
        <mesh position={[0, 0.26, 0]} receiveShadow>
          <cylinderGeometry args={[radius * 0.95, radius * 0.95, 0.05, 64]} />
          <meshStandardMaterial color="#a1a1aa" roughness={1.0} />
        </mesh>
      </group>
    </MeshErrorBoundary>
  );
}

// Renders a single mesh safely inside an error boundary
function SafeMesh({ mesh, assetManifest }: { mesh: any; assetManifest: any }) {
  try {
    let geom: ReactNode;
    const scale = mesh.scale || [1, 1, 1];
    if (mesh.type === "box") {
      geom = <boxGeometry args={scale} />;
    } else if (mesh.type === "prism") {
      geom = <coneGeometry args={[scale[0] / 2, scale[1], 4]} />;
    } else {
      geom = <boxGeometry args={scale} />;
    }

    const materialId = mesh.material_id;
    const matchingMaterial = assetManifest?.materials?.find((m: any) => m.id === materialId);
    const color = matchingMaterial?.color_hex || matchingMaterial?.color || "#cbd5e1";
    const roughness = matchingMaterial?.roughness ?? 0.8;
    const metallic = matchingMaterial?.metallic ?? 0.1;

    return (
      <mesh
        key={mesh.id}
        position={mesh.position || [0, 0, 0]}
        rotation={mesh.rotation || [0, 0, 0]}
        castShadow
        receiveShadow
      >
        {geom}
        <meshStandardMaterial
          color={color}
          roughness={roughness}
          metallic={metallic}
          transparent={matchingMaterial?.transparent}
          opacity={matchingMaterial?.opacity ?? 1.0}
        />
      </mesh>
    );
  } catch (e) {
    console.warn("SafeMesh render error for", mesh?.id, e);
    return null;
  }
}

function SafeFurniture({ item }: { item: any }) {
  try {
    return (
      <mesh key={item.id} position={item.position || [0, 0.5, 0]} castShadow receiveShadow>
        <boxGeometry args={[item.width || 1.2, item.height || 0.7, item.depth || 1.2]} />
        <meshStandardMaterial color="#e7cbcb" roughness={0.4} />
      </mesh>
    );
  } catch (e) {
    console.warn("SafeFurniture error for", item?.id, e);
    return null;
  }
}

// Procedural Geometry renderer with component filtering
function ProceduralScene() {
  const geometryData = useStore((state) => state.geometryData);
  const assetManifest = useStore((state) => state.assetManifest);
  const filter = useStore((state) => state.visibleComponentGroup);

  if (!geometryData || !geometryData.meshes) {
    return (
      <MeshErrorBoundary>
        <group>
          <mesh position={[0, 0.1, 0]}>
            <boxGeometry args={[8, 0.2, 10]} />
            <meshStandardMaterial color="#cbd5e1" roughness={0.7} />
          </mesh>
          <mesh position={[0, 1.6, 0]}>
            <boxGeometry args={[7.8, 2.8, 9.8]} />
            <meshStandardMaterial color="#e2e8f0" roughness={0.8} wireframe />
          </mesh>
        </group>
      </MeshErrorBoundary>
    );
  }

  const filteredMeshes = (geometryData.meshes || []).filter((mesh: any) => {
    if (filter === "All") return true;
    return mesh.component_group === filter;
  });

  return (
    <MeshErrorBoundary>
      <group>
        {filteredMeshes.map((mesh: any) => (
          <SafeMesh key={mesh.id} mesh={mesh} assetManifest={assetManifest} />
        ))}
        {(filter === "All" || filter === "Floor Slabs") && (assetManifest?.furniture || []).map((item: any) => (
          <SafeFurniture key={item.id} item={item} />
        ))}
      </group>
    </MeshErrorBoundary>
  );
}

export default function ThreeJSViewer() {
  const isDroneFlying = useStore((state) => state.isDroneFlying);
  const activeProjection = useStore((state) => state.activeProjection);
  const enableOrbit = !isDroneFlying && !activeProjection.startsWith("orthographic") && !activeProjection.startsWith("oblique");

  return (
    <div className="relative w-full h-full">
      <Canvas
        camera={{ position: [15, 12, 15], fov: 60 }}
        shadows
        gl={{ preserveDrawingBuffer: true }}
      >
        <React.Suspense fallback={null}>
          <color attach="background" args={["#18181b"]} />
          <ambientLight intensity={0.4} />
          <directionalLight
            position={[10, 20, 10]}
            intensity={1.2}
            castShadow
            shadow-mapSize={[2048, 2048]}
            shadow-bias={-0.0001}
          />
          <pointLight position={[-15, 10, -15]} intensity={0.5} color="#e0e7ff" />
          <Environment preset="city" />
          <Center top position={[0, 0, 0]}>
            <MeshErrorBoundary>
              <PlotLand />
            </MeshErrorBoundary>
            <MeshErrorBoundary>
              <ProceduralScene />
            </MeshErrorBoundary>
            <ContactShadows
              position={[0, 0.01, 0]}
              opacity={0.7}
              scale={40}
              blur={2.5}
              far={10}
              resolution={512}
              color="#000000"
            />
          </Center>
          {enableOrbit && (
            <OrbitControls
              maxPolarAngle={Math.PI / 2 - 0.1}
              autoRotate
              autoRotateSpeed={0.5}
              enableDamping
            />
          )}
          <ProjectionCameraController />
        </React.Suspense>
      </Canvas>
    </div>
  );
}
