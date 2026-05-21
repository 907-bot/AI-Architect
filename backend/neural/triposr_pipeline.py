"""
TripoSR Implementation - Fast Feed-Forward 3D Reconstruction
Takes a single image and generates a 3D mesh (.obj / .glb).
"""
import torch
import numpy as np
from PIL import Image
import io
import os
import structlog
from typing import Optional

# These require: pip install tsr (TripoSR official repo)
try:
    from tsr.system import TSR
    from tsr.utils import remove_background, resize_foreground
    TRIPOSR_AVAILABLE = True
except ImportError:
    TRIPOSR_AVAILABLE = False

log = structlog.get_logger()

class TripoSRPipeline:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        
    def load_model(self):
        if not TRIPOSR_AVAILABLE:
            log.warning("triposr_not_installed", message="tsr module not found. Skipping model load.")
            return
            
        if self.model is None:
            log.info("loading_triposr", device=self.device)
            # Load the pre-trained TripoSR model
            self.model = TSR.from_pretrained(
                "stabilityai/TripoSR",
                config_name="config.yaml",
                weight_name="model.ckpt"
            )
            self.model.renderer.set_chunk_size(8192)
            self.model.to(self.device)
            
    def generate_3d_from_image(self, image_path: str, output_path: str, remove_bg: bool = True) -> Optional[str]:
        """
        Generate a 3D mesh from a single 2D image.
        Returns the path to the generated .obj file.
        """
        self.load_model()
        if not self.model:
            return None
            
        try:
            log.info("processing_image_triposr", image_path=image_path)
            image = Image.open(image_path).convert("RGB")
            
            # Preprocess image
            if remove_bg:
                image = remove_background(image, rembg_session=None)
            image = resize_foreground(image, 0.85)
            
            # Run model inference
            with torch.no_grad():
                scene_codes = self.model([image], device=self.device)
                
            # Extract mesh
            meshes = self.model.extract_mesh(scene_codes, resolution=256)
            
            # Save mesh
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            mesh = meshes[0]
            
            # Use trimesh to save
            import trimesh
            trimesh_mesh = trimesh.Trimesh(vertices=mesh.v.cpu().numpy(), faces=mesh.f.cpu().numpy())
            trimesh_mesh.export(output_path)
            
            log.info("triposr_generation_complete", output_path=output_path)
            return output_path
            
        except Exception as e:
            log.error("triposr_error", error=str(e))
            return None
