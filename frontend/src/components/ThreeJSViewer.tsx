"use client";

import React, {
  useEffect, useRef, Component, ErrorInfo, ReactNode,
  useMemo, useState, useCallback,
} from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, ContactShadows, Sky, Html, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { useStore, PlacedAsset } from "@/lib/store";
import { API_BASE } from "@/lib/mvpScene";

// ─── Error Boundary ───────────────────────────────────────────────────────────
class MeshBoundary extends Component<{ children: ReactNode; fallback?: ReactNode }, { err: boolean }> {
  state = { err: false };
  static getDerivedStateFromError() { return { err: true }; }
  componentDidCatch(e: Error) { console.warn("R3F:", e.message); }
  render() { return this.state.err ? (this.props.fallback ?? null) : this.props.children; }
}

// ─── Camera Rig ───────────────────────────────────────────────────────────────
function CameraRig({ orbitRef }: { orbitRef: React.MutableRefObject<any> }) {
  const { camera } = useThree();
  const proj      = useStore(s => s.activeProjection);
  const isDrone   = useStore(s => s.isDroneFlying);
  const dronePath = useStore(s => s.dronePath);
  const kf        = useStore(s => s.currentDroneKeyframe);
  const setKf     = useStore(s => s.setDroneKeyframe);
  const progress  = useRef(0);
  const prevProj  = useRef(proj);

  useEffect(() => {
    if (prevProj.current === proj) return;
    prevProj.current = proj;
    if (orbitRef.current) orbitRef.current.enabled = false;

    const p = camera as THREE.PerspectiveCamera;
    if      (proj === "orthographic_top")   { camera.position.set(0, 60, 0.01); camera.lookAt(0,0,0); }
    else if (proj === "orthographic_front") { camera.position.set(0, 8, 55);    camera.lookAt(0,8,0); }
    else if (proj === "orthographic_side")  { camera.position.set(55,8, 0);     camera.lookAt(0,8,0); }
    else if (proj === "isometric")          { camera.position.set(28,28,28);    camera.lookAt(0,4,0); }
    else if (proj === "perspective_1p")     { p.fov=42; camera.position.set(0,5,28);   camera.lookAt(0,5,0); }
    else if (proj === "perspective_3p")     { p.fov=70; camera.position.set(22,24,22); camera.lookAt(0,4,0); }
    else                                    { p.fov=55; camera.position.set(22,14,22); camera.lookAt(0,4,0); }
    p.updateProjectionMatrix?.();

    if (orbitRef.current) {
      orbitRef.current.target.set(0,4,0);
      orbitRef.current.update();
      setTimeout(() => { if (orbitRef.current) orbitRef.current.enabled = true; }, 80);
    }
  }, [proj, camera, orbitRef]);

  useFrame((_, dt) => {
    if (!isDrone || !dronePath?.length) return;
    const cur = dronePath[kf];
    const nxt = dronePath[(kf+1) % dronePath.length];
    progress.current += dt / (cur.duration_s || 4);
    const t = Math.min(progress.current, 1);
    camera.position.lerpVectors(new THREE.Vector3(...cur.position), new THREE.Vector3(...nxt.position), t);
    camera.lookAt(new THREE.Vector3(...(cur.look_at || [0,4,0])));
    if (t >= 1) { progress.current = 0; setKf((kf+1) % dronePath.length); }
  });
  return null;
}

// ─── Walkthrough (First Person, NO pointer lock — uses mouse drag) ────────────
export function WalkthroughController({ canvasRef }: { canvasRef: React.RefObject<HTMLDivElement> }) {
  const { camera } = useThree();
  const isWalk  = useStore(s => s.isWalkthrough);
  const setWalk = useStore(s => s.setWalkthrough);
  const keys    = useRef<Set<string>>(new Set());
  const yaw     = useRef(0);
  const pitch   = useRef(0);
  const dragging = useRef(false);
  const lastMouse = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (!isWalk) return;
    camera.position.set(0, 1.7, 8);
    yaw.current = 0; pitch.current = 0;
  }, [isWalk, camera]);

  useEffect(() => {
    if (!isWalk) return;
    const onDown = (e: MouseEvent) => { dragging.current = true; lastMouse.current = { x: e.clientX, y: e.clientY }; };
    const onUp   = () => { dragging.current = false; };
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      yaw.current   -= (e.clientX - lastMouse.current.x) * 0.003;
      pitch.current -= (e.clientY - lastMouse.current.y) * 0.003;
      pitch.current  = Math.max(-1.1, Math.min(1.1, pitch.current));
      lastMouse.current = { x: e.clientX, y: e.clientY };
    };
    const onKey  = (e: KeyboardEvent) => {
      keys.current.add(e.code);
      if (e.code === "Escape") setWalk(false);
    };
    const offKey = (e: KeyboardEvent) => keys.current.delete(e.code);

    window.addEventListener("mousedown", onDown);
    window.addEventListener("mouseup", onUp);
    window.addEventListener("mousemove", onMove);
    window.addEventListener("keydown", onKey);
    window.addEventListener("keyup", offKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("mouseup", onUp);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("keyup", offKey);
    };
  }, [isWalk, setWalk]);

  useFrame((_, dt) => {
    if (!isWalk) return;
    const speed = keys.current.has("ShiftLeft") ? 7 : 3.5;
    const dir = new THREE.Vector3(0,0,-1).applyEuler(new THREE.Euler(0, yaw.current, 0));
    const right = dir.clone().cross(new THREE.Vector3(0,1,0));

    if (keys.current.has("KeyW") || keys.current.has("ArrowUp"))    camera.position.addScaledVector(dir, speed*dt);
    if (keys.current.has("KeyS") || keys.current.has("ArrowDown"))  camera.position.addScaledVector(dir, -speed*dt);
    if (keys.current.has("KeyA") || keys.current.has("ArrowLeft"))  camera.position.addScaledVector(right, -speed*dt);
    if (keys.current.has("KeyD") || keys.current.has("ArrowRight")) camera.position.addScaledVector(right, speed*dt);

    camera.rotation.order = "YXZ";
    camera.rotation.y = yaw.current;
    camera.rotation.x = pitch.current;
    if (camera.position.y < 1.5) camera.position.y = 1.5;
  });
  return null;
}

// ─── Ground ───────────────────────────────────────────────────────────────────
function Ground() {
  const pw = useStore(s => s.plotWidth);
  const pd = useStore(s => s.plotDepth);
  return (
    <group>
      <mesh rotation={[-Math.PI/2, 0, 0]} position={[0,-0.01,0]} receiveShadow>
        <circleGeometry args={[Math.max(pw,pd)*4, 64]} />
        <meshStandardMaterial color="#4a8a4a" roughness={1} />
      </mesh>
      <mesh rotation={[-Math.PI/2, 0, 0]} position={[0,0,0]} receiveShadow>
        <planeGeometry args={[pw*1.2, pd*1.2]} />
        <meshStandardMaterial color="#9e9d96" roughness={0.95} />
      </mesh>
    </group>
  );
}

// ─── Compass ─────────────────────────────────────────────────────────────────
function CompassOverlay() {
  return (
    <Html position={[0,0,0]} style={{ pointerEvents:"none", userSelect:"none" }}>
      {/* Rendered via DOM overlay below */}
    </Html>
  );
}

// ─── Trees — FIXED: positions use [x, y=0, z] ─────────────────────────────────
function Tree({ pos }: { pos: [number, number, number] }) {
  const h = 4.5 + (Math.abs(pos[0]) * 0.17) % 3.0;
  const r = 1.6 + (Math.abs(pos[2]) * 0.09) % 1.2;
  const colors = ["#2d6e2d","#3a8a3a","#1e5c1e"];
  return (
    <group position={pos}>
      {/* Trunk — always starts at y=0 */}
      <mesh position={[0, h*0.15, 0]} castShadow>
        <cylinderGeometry args={[0.14, 0.22, h*0.3, 8]} />
        <meshStandardMaterial color="#5c3d1e" roughness={0.9} />
      </mesh>
      {/* Canopy layers */}
      {[0.55, 0.44, 0.34].map((yf, i) => (
        <mesh key={i} position={[0, h*yf + h*0.3/2, 0]} castShadow>
          <coneGeometry args={[r*(1-i*0.22), h*(0.42-i*0.07), 9]} />
          <meshStandardMaterial color={colors[i]} roughness={0.85} />
        </mesh>
      ))}
    </group>
  );
}

function Trees() {
  const pw = useStore(s => s.plotWidth);
  const pd = useStore(s => s.plotDepth);
  // FIXED: format is [x, 0, z] — Y is UP in Three.js, Z is depth
  const positions = useMemo<[number,number,number][]>(() => {
    const hw = pw/2, hd = pd/2;
    return [
      [-hw-5, 0,  hd+6],   // back-left
      [ hw+5, 0,  hd+6],   // back-right
      [0,     0,  hd+7],   // back-centre
      [-hw-6, 0,  hd/2],   // mid-left
      [ hw+6, 0,  hd],     // mid-right-back
      [-hw-9, 0, -hd-6],   // far front-left
      [ hw+9, 0, -hd-6],   // far front-right
      [-hw-4, 0,  hd+2],   // back-left cluster
    ];
  }, [pw, pd]);
  return <>{positions.map((pos,i) => <Tree key={i} pos={pos} />)}</>;
}

// ─── Component filter map for GLB ─────────────────────────────────────────────
const COMPONENT_PREFIXES: Record<string, string[]> = {
  "All":         [],
  "Foundation":  ["Foundation","Plinth","BasePad","Ground","Grass","Path"],
  "Floor Slabs": ["Slab_","SlabEdge_"],
  "Walls":       ["Wall_","Lobby_Wall","StairCore"],
  "Windows":     ["Win_","Lobby_Glass","glass"],
  "Doors":       ["Lobby_Door","GDoor","Door"],
  "Roof":        ["Roof_","Par_","Cap_","Ridge","Hip","Pitch","Eave","Gutter","Skylight","Dormer"],
  "Interior":    ["Stair_","Lobby","Room","Floor_Mat","Furniture","Bed","Sofa","Kitchen","Bath"],
};

// ─── GLB Viewer with component filter ────────────────────────────────────────
function FilteredGLB({ path, filter }: { path: string; filter: string }) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const { scene } = useGLTF(url);
  const groupRef  = useRef<THREE.Group>(null!);
  const cloned    = useMemo(() => scene.clone(), [scene]);

  useEffect(() => {
    if (!groupRef.current) return;
    const box = new THREE.Box3().setFromObject(groupRef.current);
    const sz  = box.getSize(new THREE.Vector3());
    const s   = Math.max(sz.x,sz.y,sz.z) > 0 ? 18/Math.max(sz.x,sz.y,sz.z) : 1;
    groupRef.current.scale.setScalar(s);
    const nb  = new THREE.Box3().setFromObject(groupRef.current);
    groupRef.current.position.y = -nb.min.y;
    groupRef.current.traverse(c => {
      if ((c as THREE.Mesh).isMesh) { c.castShadow=true; c.receiveShadow=true; }
    });
  }, [path]);

  useEffect(() => {
    if (!groupRef.current) return;
    const prefixes = COMPONENT_PREFIXES[filter] ?? [];
    groupRef.current.traverse(c => {
      if (!(c as THREE.Mesh).isMesh) return;
      const name = c.name || c.parent?.name || "";
      c.visible = prefixes.length === 0 || prefixes.some(p => name.startsWith(p));
    });
  }, [filter]);

  return <group key={path}><primitive ref={groupRef} object={cloned} /></group>;
}

// ─── Procedural fallback ──────────────────────────────────────────────────────
function ProceduralScene() {
  const geo = useStore(s => s.geometryData);
  const manifest = useStore(s => s.assetManifest);
  const filter = useStore(s => s.visibleComponentGroup);
  const materials = manifest?.materials || [];
  if (!geo?.meshes?.length) return <EmptyBuilding />;
  const meshes = geo.meshes.filter((m:any) => filter==="All" || m.component_group===filter);
  return (
    <group>
      {meshes.map((m:any) => (
        <MeshBoundary key={m.id}>
          <mesh position={m.position} rotation={m.rotation||[0,0,0]} castShadow receiveShadow>
            <boxGeometry args={m.scale||[1,1,1]} />
            <meshStandardMaterial color={materials.find((mat:any)=>(mat.id||mat.material_id)===m.material_id)?.color_hex||"#c8cdd4"} />
          </mesh>
        </MeshBoundary>
      ))}
    </group>
  );
}

function EmptyBuilding() {
  const mesh = useRef<THREE.Mesh>(null!);
  useFrame(({clock}) => {
    if (mesh.current) {
      mesh.current.rotation.y = clock.getElapsedTime()*0.3;
      mesh.current.position.y = 2 + Math.sin(clock.getElapsedTime()*0.8)*0.2;
    }
  });
  return (
    <group>
      <mesh ref={mesh} position={[0,2,0]} castShadow>
        <boxGeometry args={[3,4,3]} />
        <meshPhysicalMaterial color="#e2e8f0" roughness={0.3} metalness={0.1} wireframe />
      </mesh>
      <Html center position={[0,5.5,0]}>
        <div className="pointer-events-none select-none text-center">
          <p className="text-[11px] font-semibold text-slate-500 bg-white/80 backdrop-blur px-3 py-1.5 rounded-full shadow-sm border border-slate-200 whitespace-nowrap">
            Describe your building to get started
          </p>
        </div>
      </Html>
    </group>
  );
}

// ─── Placed assets ────────────────────────────────────────────────────────────
function PlacedAssetMesh({ asset, onSelect }: { asset: PlacedAsset; onSelect:(id:string)=>void }) {
  const selected = useStore(s=>s.selectedAssetUid)===asset.placement_id;
  const s = asset.scale||1;
  const size:[number,number,number] = [s*1.2, s*0.8, s*1.2];
  const pos:[number,number,number] = Array.isArray(asset.position)
    ? asset.position as [number,number,number]
    : [asset.position.x, asset.position.y, asset.position.z];
  return (
    <group position={pos} onClick={e=>{e.stopPropagation();onSelect(asset.placement_id);}}>
      <mesh position={[0,size[1]/2,0]} castShadow>
        <boxGeometry args={size} />
        <meshStandardMaterial color={selected?"#7c93c3":"#94a3b8"} roughness={0.6} />
      </mesh>
      {selected && (
        <mesh position={[0,size[1]/2,0]}>
          <boxGeometry args={[size[0]+0.1,size[1]+0.1,size[2]+0.1]} />
          <meshBasicMaterial color="#7c93c3" wireframe />
        </mesh>
      )}
      <Html position={[0,size[1]+0.5,0]} center>
        <span className="pointer-events-none select-none text-[9px] font-semibold bg-white/90 text-slate-700 px-2 py-0.5 rounded-full shadow-sm border border-slate-200 whitespace-nowrap">
          {asset.name}
        </span>
      </Html>
    </group>
  );
}

// ─── Main Viewer ──────────────────────────────────────────────────────────────
export default function ThreeJSViewer() {
  const isDrone      = useStore(s=>s.isDroneFlying);
  const proj         = useStore(s=>s.activeProjection);
  const placedAssets = useStore(s=>s.placedAssets);
  const addPlacedAsset    = useStore(s=>s.addPlacedAsset);
  const updatePlacedAsset = useStore(s=>s.updatePlacedAsset);
  const setSelectedAssetUid = useStore(s=>s.setSelectedAssetUid);
  const removePlacedAsset   = useStore(s=>s.removePlacedAsset);
  const generatedGlbPath    = useStore(s=>s.generatedGlbPath);
  const filter       = useStore(s=>s.visibleComponentGroup);
  const isWalk       = useStore(s=>s.isWalkthrough);

  const containerRef = useRef<HTMLDivElement>(null);
  const orbitRef     = useRef<any>(null);
  const assetCounter = useRef(0);
  const [isDragOver, setIsDragOver] = useState(false);

  const screenTo3D = useCallback((clientX:number, clientY:number) => {
    const el=containerRef.current; if(!el) return {x:0,y:0,z:0};
    const r=el.getBoundingClientRect();
    return { x:((clientX-r.left)/r.width*2-1)*12, y:0, z:((clientY-r.top)/r.height*2-1)*10 };
  }, []);

  const handleDrop = async (e:React.DragEvent) => {
    e.preventDefault(); setIsDragOver(false);
    let data:any;
    try { data=JSON.parse(e.dataTransfer.getData("application/json")||e.dataTransfer.getData("text/plain")); }
    catch { return; }
    const pos=screenTo3D(e.clientX,e.clientY);
    const offset=assetCounter.current*1.8; assetCounter.current++;
    const placementId=`placed-${Date.now()}-${data.uid}`;
    addPlacedAsset({ placement_id:placementId, asset_uid:data.uid, name:data.name,
      thumbnail:data.thumbnail||"",
      position:[pos.x+offset*Math.cos(offset),0,pos.z+offset*Math.sin(offset)],
      rotation:[0,0,0], scale:1.5 });
    try {
      const r=await fetch(`${API_BASE}/api/sketchfab/drag-drop`,{
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({asset_uid:data.uid,drop_position:{x:pos.x,y:0,z:pos.z},
          room_context:data.room_context||"interior",auto_orient:true,auto_scale:true})});
      if(r.ok) { const p=await r.json(); updatePlacedAsset(placementId,{scale:p.scale||1.5}); }
    } catch {}
  };

  useEffect(()=>{
    const onKey=(e:KeyboardEvent)=>{
      if((e.key==="Delete"||e.key==="Backspace")&&document.activeElement?.tagName!=="INPUT"){
        const sel=useStore.getState().selectedAssetUid;
        if(sel){removePlacedAsset(sel);setSelectedAssetUid(null);}
      }
    };
    window.addEventListener("keydown",onKey);
    return ()=>window.removeEventListener("keydown",onKey);
  },[removePlacedAsset,setSelectedAssetUid]);

  const canOrbit = !isDrone && !isWalk;

  return (
    <div ref={containerRef} className="absolute inset-0"
      onDragOver={e=>{e.preventDefault();setIsDragOver(true);}}
      onDragLeave={()=>setIsDragOver(false)}
      onDrop={handleDrop}
      onClick={()=>setSelectedAssetUid(null)}>

      {/* Drag overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-20 pointer-events-none border-4 border-dashed border-[#7c93c3]/60 rounded-lg flex items-center justify-center">
          <div className="bg-white/90 backdrop-blur rounded-2xl px-6 py-4 shadow-xl border border-[#7c93c3]/30">
            <p className="text-sm font-semibold text-slate-700">Drop to place in scene</p>
          </div>
        </div>
      )}

      {/* Walkthrough HUD */}
      {isWalk && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-30 pointer-events-none">
          <div className="w-4 h-4 relative">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-0.5 h-3 bg-white/80" />
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-3 h-0.5 bg-white/80" />
            </div>
          </div>
        </div>
      )}
      {isWalk && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-30 pointer-events-none bg-black/60 text-white text-[9px] rounded-xl px-4 py-2 backdrop-blur text-center">
          <p className="font-bold mb-0.5">🚶 First Person Mode</p>
          <p>WASD / Arrows — move · <span className="text-white/60">Click + drag — look · Shift — run · Esc — exit</span></p>
        </div>
      )}

      {/* GLB badge */}
      {generatedGlbPath && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 rounded-full border border-emerald-200 bg-white/90 px-3 py-1 text-[9px] font-semibold text-emerald-700 shadow backdrop-blur flex items-center gap-1.5 pointer-events-none">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
          {generatedGlbPath.split("/").pop()}
        </div>
      )}

      <Canvas
        camera={{ position:[22,14,22], fov:55, near:0.1, far:1500 }}
        shadows={{ type: THREE.PCFSoftShadowMap }}
        gl={{ antialias:true, alpha:false,
              toneMapping: THREE.ACESFilmicToneMapping,
              toneMappingExposure: 1.15 }}
        dpr={[1,2]}
        style={{ width:"100%", height:"100%" }}>

        <React.Suspense fallback={null}>
          <Sky sunPosition={[80,35,60]} turbidity={6} rayleigh={0.5} mieCoefficient={0.005} mieDirectionalG={0.8} />
          <color attach="background" args={["#d6eaf8"]} />

          <ambientLight intensity={0.6} color="#fff8f0" />
          <directionalLight position={[30,45,25]} intensity={2.0} castShadow
            shadow-mapSize={[4096,4096]} shadow-camera-far={200}
            shadow-camera-left={-60} shadow-camera-right={60}
            shadow-camera-top={60} shadow-camera-bottom={-60}
            shadow-bias={-0.0003} shadow-normalBias={0.02} />
          <directionalLight position={[-20,25,-20]} intensity={0.4} color="#c7d4f5" />
          <hemisphereLight args={["#b9d4f7","#6aab6a",0.5]} />

          <MeshBoundary><Ground /></MeshBoundary>
          <MeshBoundary><Trees /></MeshBoundary>

          {generatedGlbPath ? (
            <MeshBoundary fallback={<ProceduralScene />}>
              <FilteredGLB path={generatedGlbPath} filter={filter} />
            </MeshBoundary>
          ) : (
            <MeshBoundary><ProceduralScene /></MeshBoundary>
          )}

          {placedAssets.map(asset => (
            <MeshBoundary key={asset.placement_id}>
              <PlacedAssetMesh asset={asset} onSelect={setSelectedAssetUid} />
            </MeshBoundary>
          ))}

          <ContactShadows position={[0,0.02,0]} opacity={0.45} scale={80} blur={3} far={16} resolution={512} color="#334155" />

          {canOrbit && (
            <OrbitControls ref={orbitRef} target={[0,4,0]}
              maxPolarAngle={Math.PI/1.85} minPolarAngle={0.05}
              minDistance={5} maxDistance={150}
              enableDamping dampingFactor={0.06}
              enablePan panSpeed={0.8} rotateSpeed={0.7} zoomSpeed={1.2} />
          )}

          <CameraRig orbitRef={orbitRef} />
          <WalkthroughController canvasRef={containerRef} />
        </React.Suspense>
      </Canvas>
    </div>
  );
}
