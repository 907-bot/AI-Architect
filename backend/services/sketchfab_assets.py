"""
Sketchfab Asset Integration
Downloads and manages pre-made 3D architectural models
"""
import os
import json
import hashlib
import urllib.request
import zipfile
from typing import Dict, List, Optional, Tuple

# Cache directory for downloaded models
CACHE_DIR = "/tmp/sketchfab_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Curated asset IDs (free models suitable for architecture)
# Format: {category: {name: sketchfab_model_id}}
ASSETS = {
    "windows": {
        "modern_window": "a4c450454f4c4969a8f7a0d0c0e5c0b0d",  # Example ID
        "french_window": "b5d561565g5d5070b9g8b1e1d6f1d0c1e",
        "casement": "c6e672676h6e6181c0h9c2f2e7g2e1d2f",
    },
    "doors": {
        "modern_door": "d7f783787i7f7292d1i0d3g3f8h3f2e3g",
        "double_door": "e8g894898g8g8303e2j1e4h4g9i4g3f4h",
        "sliding": "f9h9a59a9h9h9414f3j2f5i5h9h5i4g5i",
    },
    "roofs": {
        "tile_roof": "g0i0b6b0i0i0525g4k3g6j0i0j6j5h6j",
        "metal_roof": "h1j1c7c1j1j1636h5l4h7k1j1k7k6i7k",
    },
    "furniture": {
        "sofa": "i2k2d8d2k2k2747i6m5i8l2k2l8l7j8l",
        "table": "j3l3e9e3l3l3858j7n6j9m3l3l9m8k9m",
        "chair": "k4m4f0f4m4m4969k8o7k0n4m4m0n9l0n",
    },
    "plants": {
        "potted_plant": "l5n5g1g5n5n5070l9p8l1o5n5n1o0m1o",
        "tree": "m6o6h2h6o6o6181m0q9m2p6o6o2p1n2p",
    }
}

class SketchfabAssetManager:
    """Manages downloading and loading Sketchfab models"""
    
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir
        self.downloaded: Dict[str, str] = {}  # model_id -> local_path
        
    def get_asset_url(self, model_id: str) -> str:
        """Get download URL for a model"""
        # Sketchfab API endpoint for downloading
        # In production, use actual API with认证
        return f"https://sketchfab.com/models/{model_id}/download"
    
    def download_model(self, model_id: str, category: str = "windows") -> Optional[str]:
        """Download a model by ID"""
        if model_id in self.downloaded:
            return self.downloaded[model_id]
        
        # Check if already cached
        cache_path = os.path.join(self.cache_dir, f"{model_id}.glb")
        if os.path.exists(cache_path):
            self.downloaded[model_id] = cache_path
            return cache_path
        
        # For demo, we'll use a placeholder
        # In production, actual API download:
        # url = f"https://api.sketchfab.com/v3/models/{model_id}"
        # This would require API token
        return None
    
    def list_available(self, category: str) -> List[Dict]:
        """List available assets in a category"""
        return [
            {"id": ASSETS[category][name], "name": name}
            for name in ASSETS.get(category, {})
        ]
    
    def search_sketchfab(self, query: str, api_key: str = "") -> List[Dict]:
        """Search Sketchfab via API (requires API key)"""
        if not api_key:
            return []
        
        url = "https://api.sketchfab.com/v3/search"
        params = f"?q={query}&type=models&downloadable=true"
        
        req = urllib.request.Request(url + params)
        req.add_header("Authorization", f"Token {api_key}")
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
                return [
                    {"uid": r["uid"], "name": r["name"]}
                    for r in data.get("results", [])[:10]
                ]
        except Exception as e:
            print(f"Search failed: {e}")
            return []


class AssetComposer:
    """Compose buildings from pre-made assets"""
    
    def __init__(self):
        self.manager = SketchfabAssetManager()
        
    def compose_building(self, spec: Dict) -> Tuple[List[Dict], List[Dict]]:
        """
        Compose building from selected assets plus generated parts
        
        Returns: (meshes_dict_list, materials_list)
        """
        meshes = []
        
        # Use assets where specified
        if spec.get("use_assets"):
            categories = spec.get("assets", {})
            for category, asset_name in categories.items():
                if category in ASSETS and asset_name in ASSETS[category]:
                    model_id = ASSETS[category][asset_name]
                    # In production, would load actual GLB
                    # For now, generate representative box
                    meshes.append({
                        "position": [0, 0, 0],
                        "scale": [1, 0.1, 1],
                        "material_id": "concrete",
                        "component_group": f"Asset_{category}",
                        "asset_id": model_id
                    })
        
        # Add generated parts (foundation, walls, etc.)
        meshes.extend(self._generate_base(spec))
        
        return meshes, []
    
    def _generate_base(self, spec: Dict) -> List[Dict]:
        """Generate base building elements"""
        meshes = []
        pw = spec.get("width", 10) * 0.1
        pd = spec.get("depth", 8) * 0.1
        fh = spec.get("floor_height", 3) * 0.1
        
        # Foundation
        meshes.append({
            "position": [0, -0.015, 0],
            "scale": [pw + 0.1, 0.03, pd + 0.1],
            "material_id": "concrete",
            "component_group": "Foundation"
        })
        
        # Walls
        for floor in range(spec.get("floors", 2)):
            y = floor * fh + fh/2 + 0.1
            meshes.append({
                "position": [0, y, 0],
                "scale": [pw * 0.95, fh * 0.92, pd * 0.95],
                "material_id": spec.get("wall_material", "plaster_white"),
                "component_group": f"Walls_Floor{floor+1}"
            })
        
        return meshes


# Singleton
asset_manager = SketchfabAssetManager()
asset_composer = AssetComposer()