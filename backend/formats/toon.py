"""
TOON - Token Oriented Object Notation
A compact format for 3D mesh data communication
"""

import re
from typing import Dict, Any, List, Tuple

# Format specification:
# MESH|[position]|[scale]|[material_id]|[component_group]
# example: MESH|0.0,0.25,0.0|2.0,0.25,3.0|plaster_white|Exterior
#
# MATERIAL|id|color_hex|roughness|metallic
# example: MATERIAL|concrete|#9d9d9d|0.85|0.0

def encode_mesh(mesh: Dict) -> str:
    """Encode a mesh dict to TOON format"""
    pos = ",".join(str(v) for v in mesh.get("position", [0,0,0]))
    scl = ",".join(str(v) for v in mesh.get("scale", [1,1,1]))
    mat = mesh.get("material_id", "default")
    grp = mesh.get("component_group", "Uncategorized")
    return f"MESH|{pos}|{scl}|{mat}|{grp}"

def decode_mesh(toon: str) -> Dict:
    """Decode TOON string to mesh dict"""
    parts = toon.split("|")
    if len(parts) < 5 or parts[0] != "MESH":
        return {}
    return {
        "position": [float(v) for v in parts[1].split(",")],
        "scale": [float(v) for v in parts[2].split(",")],
        "material_id": parts[3],
        "component_group": parts[4]
    }

def encode_material(mat: Dict) -> str:
    """Encode material to TOON format"""
    mid = mat.get("material_id", mat.get("id", "default"))
    color = mat.get("color_hex", mat.get("c", "#808080"))
    rough = mat.get("roughness", mat.get("r", 0.5))
    metal = mat.get("metallic", mat.get("m", 0.0))
    trans = mat.get("transmission", "")
    trans_str = f"|{trans}" if trans else ""
    return f"MATERIAL|{mid}|{color}|{rough}|{metal}{trans_str}"

def decode_material(toon: str) -> Dict:
    """Decode TOON string to material dict"""
    parts = toon.split("|")
    if len(parts) < 4 or parts[0] != "MATERIAL":
        return {}
    result = {
        "material_id": parts[1],
        "color_hex": parts[2],
        "roughness": float(parts[3]),
        "metallic": float(parts[4]) if len(parts) > 4 else 0.0
    }
    if len(parts) > 5 and parts[5]:
        result["transmission"] = float(parts[5])
    return result

def encode_scene(meshes: List[Dict], materials: List[Dict], metadata: Dict = None) -> str:
    """Encode entire scene to TOON format"""
    lines = ["# TOON SCENE v1.0"]
    
    # Metadata
    if metadata:
        for k, v in metadata.items():
            lines.append(f"META|{k}|{v}")
    
    # Materials
    lines.append("# MATERIALS")
    for mat in materials:
        lines.append(encode_material(mat))
    
    # Meshes
    lines.append("# MESHES")
    for mesh in meshes:
        lines.append(encode_mesh(mesh))
    
    return "\n".join(lines)

def decode_scene(toon_text: str) -> Tuple[List[Dict], List[Dict], Dict]:
    """Decode TOON string to scene components"""
    meshes = []
    materials = []
    metadata = {}
    in_meshes = False
    in_materials = False
    
    for line in toon_text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            in_meshes = line == "# MESHES"
            in_materials = line == "#MATERIALS"
            continue
        
        if line.startswith("META|"):
            parts = line.split("|")
            if len(parts) >= 3:
                metadata[parts[1]] = parts[2]
        elif line.startswith("MATERIAL|") and in_materials:
            materials.append(decode_material(line))
        elif line.startswith("MESH|") and in_meshes:
            meshes.append(decode_mesh(line))
    
    return meshes, materials, metadata

# Compact single-line format for network transfer
def encode_compact(meshes: List[Dict], materials: List[Dict]) -> str:
    """Compact one-line format: MESH[pos,scale,mat,grp];MESH[...]...||MAT[id,c,r,m];MAT[...]"""
    mesh_tokens = [encode_mesh(m) for m in meshes]
    mat_tokens = [encode_material(m) for m in materials]
    return ";".join(mesh_tokens) + "||" + ";".join(mat_tokens)

def decode_compact(toon: str) -> Tuple[List[Dict], List[Dict]]:
    """Decode compact format"""
    if "||" not in toon:
        return [], []
    mesh_part, mat_part = toon.split("||")
    meshes = [decode_mesh(m) for m in mesh_part.split(";") if m.startswith("MESH")]
    materials = [decode_material(m) for m in mat_part.split(";") if m.startswith("MATERIAL")]
    return meshes, materials
