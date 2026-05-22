"""Procedural Building Generator"""
import uuid
from typing import Dict, Any, List

# PBR Materials
MAT = {
    "concrete": {"c": "#b8b8b8", "r": 0.9, "m": 0.0},
    "brick": {"c": "#8b4513", "r": 0.85, "m": 0.0},
    "plaster": {"c": "#f5f5f0", "r": 0.8, "m": 0.0},
    "glass": {"c": "#fff", "r": 0.1, "m": 0.1, "o": 0.3},
    "wood": {"c": "#8b5a2b", "r": 0.6, "m": 0.0},
    "metal": {"c": "#333", "r": 0.3, "m": 0.8},
    "roof": {"c": "#654321", "r": 0.7, "m": 0.0},
    "grass": {"c": "#32cd32", "r": 0.95, "m": 0.0},
    "limestone": {"c": "#d9d0c1", "r": 0.75, "m": 0.0},
}

def gen_building(btype="villa", style="modern", floors=2, pw=20, pd=30, beds=3, garage=True, pool=False, garden=True) -> Dict:
    pw *= 0.1  # Scale for Three.js viewer
    pd *= 0.1
    m, hpf = [], 3.0
    mt = "plaster" if style=="modern" else "brick"
    rm = "metal" if style=="modern" else "roof"
    
    # Foundation
    m.append({"id": f"found_{uuid.uuid4().hex[:4]}", "grp": "Foundation", "type": "box", "pos": [0,-0.25,0], "scl": [pw,0.05,pd], "mid": "concrete"})
    
    for f in range(floors):
        y = f*hpf+1.5
        m.append({"id": f"wall_{f}_{uuid.uuid4().hex[:4]}", "grp": "Walls", "type": "box", "pos": [0,y,0], "scl": [pw*0.9,hpf*0.1,pd*0.9], "mid": mt})
        m.append({"id": f"wnd_{f}f_{uuid.uuid4().hex[:4]}", "grp": "Openings", "type": "box", "pos": [0,y,pd*0.45], "scl": [pw*0.25,hpf*0.4,0.01], "mid": "glass"})
        m.append({"id": "wnd_{f}b_"+uuid.uuid4().hex[:4], "grp": "Openings", "type": "box", "pos": [0,y,-pd*0.45], "scl": [pw*0.25,hpf*0.4,0.01], "mid": "glass"})
    
    # Entrance
    m.append({"id": "door_"+uuid.uuid4().hex[:4], "grp": "Openings", "type": "box", "pos": [0,1.1,pd/2-0.1], "scl": [1,2.2,0.1], "mid": "wood"})
    m.append({"id": "canopy_"+uuid.uuid4().hex[:4], "grp": "Entrance", "type": "box", "pos": [0,2.5,pd/2+0.3], "scl": [1.5,0.1,0.8], "mid": "concrete"})
    
    # Roof
    rl = floors*hpf
    m.append({"id": "roof_"+uuid.uuid4().hex[:4], "grp": "Roof", "type": "box", "pos": [0,rl+0.1,0], "scl": [pw*0.95,0.2,pd*0.95], "mid": rm})
    
    if garage:
        m.append({"id": "garage_"+uuid.uuid4().hex[:4], "grp": "Ancillary", "type": "box", "pos": [-pw/2-2,1.5,-3], "scl": [4,2.5,5], "mid": mt})
        m.append({"id": "gardoor_"+uuid.uuid4().hex[:4], "grp": "Ancillary", "type": "box", "pos": [-pw/2-2,1.25,-0.4], "scl": [3.5,2.2,0.1], "mid": "metal"})
    
    if pool:
        m.append({"id": "pool_"+uuid.uuid4().hex[:4], "grp": "Landscape", "type": "box", "pos": [pw/3,-0.3,-pd/4], "scl": [6,1.2,4], "mid": "glass"})
    
    if garden:
        m.append({"id": "ground_"+uuid.uuid4().hex[:4], "grp": "Landscape", "type": "box", "pos": [0,-0.05,0], "scl": [pw+8,0.1,pd+8], "mid": "grass"})
    
    # Fence
    fh = 1.5
    for side in ["front","back","left","right"]:
        s = 1 if side=="front" else 0.1
        m.append({"id": f"fence_{side}_"+uuid.uuid4().hex[:4], "grp": "Boundary", "type": "box", "pos": [pw/2+0.1,fh/2,0] if side=="right" else [0,fh/2,pd/2+0.1] if side=="front" else [-pw/2-0.1,fh/2,0], "scl": [0.1,fh,pd] if side=="right" else [pw,fh,0.1] if side=="front" or side=="back" else [0.1,fh,pd], "mid": "metal"})
    
    # Materials list
    mats = [{"id": k, "c": v["c"], "r": v["r"], "m": v["m"]} for k,v in MAT.items()]
    
    return {"meshes": m, "materials": mats, "meta": {"type": btype, "style": style, "floors": floors, "elements": len(m)}}

def generate_building(**kw): return gen_building(**kw)