"""
Chat Agent - Allows modify after generation
"""
from typing import Dict, List, Optional

FEATURES = {
    "garage": lambda m, c: m.extend([
        {"position": [-2.4, 0.17, -0.45], "scale": [0.5, 0.32, 0.6], "material_id": "plaster_white", "component_group": "Garage"},
        {"position": [-2.4, 0.17, -0.14], "scale": [0.35, 0.22, 0.02], "material_id": "metal_dark", "component_group": "Garage"}
    ]),
    "pool": lambda m, c: m.extend([
        {"position": [0.24, -0.03, -1.2], "scale": [0.7, 0.015, 0.5], "material_id": "patio_stone", "component_group": "Pool"},
        {"position": [0.24, 0.0, -1.2], "scale": [0.62, 0.15, 0.42], "material_id": "glass_tinted", "component_group": "Pool"}
    ]),
    "garden": lambda m, c: m.extend([
        {"position": [0, -0.06, 0], "scale": [3.1, 0.025, 4.2], "material_id": "grass", "component_group": "Landscape"}
    ]),
    "chimney": lambda m, c: m.append(
        {"position": [0.7, 0.62, 0.9], "scale": [0.08, 0.2, 0.08], "material_id": "brick_red", "component_group": "Chimney"}
    ),
    "terrace": lambda m, c: m.append(
        {"position": [0.6, 0.03, 1.9], "scale": [0.4, 0.02, 0.25], "material_id": "patio_stone", "component_group": "Terrace"}
    ),
    "balcony": lambda m, c: m.append(
        {"position": [0.6, 0.32, 1.5], "scale": [0.3, 0.02, 0.15], "material_id": "patio_stone", "component_group": "Balcony"}
    ),
    "porch": lambda m, c: m.extend([
        {"position": [0.36, 0.2, 1.65], "scale": [0.04, 0.4, 0.04], "material_id": "plaster_white", "component_group": "Porch"},
        {"position": [0, 0.42, 1.65], "scale": [0.25, 0.025, 0.18], "material_id": "roof_slate", "component_group": "Porch"}
    ]),
    "fence": lambda m, c: m.extend([
        {"position": [0, 0.075, 3.08], "scale": [3.2, 0.15, 0.015], "material_id": "metal_dark", "component_group": "Boundary"},
        {"position": [-2.08, 0.075, 0], "scale": [0.015, 0.15, 3.15], "material_id": "metal_dark", "component_group": "Boundary"},
        {"position": [2.08, 0.075, 0], "scale": [0.015, 0.15, 3.15], "material_id": "metal_dark", "component_group": "Boundary"}
    ])
}

REMOVE_IDS = {
    "garage": ["Garage"],
    "pool": ["Pool"], 
    "garden": ["Landscape"],
    "chimney": ["Chimney"],
    "terrace": ["Terrace"],
    "balcony": ["Balcony"],
    "porch": ["Porch"],
    "fence": ["Boundary"]
}

class ChatArchitect:
    def __init__(self):
        self.building = None
        self.materials = None
        
    def modify(self, cmd: str):
        if not self.building:
            return {"error": "No building. Generate first."}
        
        cmd = cmd.lower()
        is_add = cmd.startswith(("add", "include", "put", "with"))
        is_remove = cmd.startswith(("remove", "delete", "without", "no"))
        
        feat = next((f for f in FEATURES if f in cmd), None)
        
        if not feat:
            return {"error": "Try: add garage, remove pool, add terrace, remove fence", "options": list(FEATURES.keys())}
        
        if is_add:
            FEATURES[feat](self.building, {})
            msg = f"Added {feat}. Want more changes?"
        elif is_remove:
            target_grp = REMOVE_IDS.get(feat, [feat])
            self.building = [m for m in self.building if m.get("component_group", "") not in target_grp]
            msg = f"Removed {feat}. Anything else?"
        else:
            return {"error": "Say 'add' or 'remove'"}
        
        return {"meshes": self.building, "materials": self.materials, "message": msg, "count": len(self.building)}


def update_building(meshes: List, materials):
    """Hook into existing architect"""
    ca = ChatArchitect()
    ca.building = meshes
    ca.materials = materials
    return ca