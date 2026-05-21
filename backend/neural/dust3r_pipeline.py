"""
DUSt3R Implementation - Multi-view geometry reconstruction
Used for uncalibrated image-to-3D alignment and point cloud generation.
"""
import torch
import numpy as np
from PIL import Image
import os
import structlog

# Requires DUSt3R to be installed
try:
    from dust3r.inference import inference
    from dust3r.model import AsymmetricCroCo3DSeg
    from dust3r.image_pairs import make_pairs
    from dust3r.cloud_opt import global_aligner, GlobalAlignerMode
    DUST3R_AVAILABLE = True
except ImportError:
    DUST3R_AVAILABLE = False

log = structlog.get_logger()

class DUSt3RPipeline:
    def __init__(self, model_path="naver/DUSt3R_ViTLarge_BaseDecoder_512_dpt"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_path = model_path
        self.model = None

    def load_model(self):
        if not DUST3R_AVAILABLE:
            log.warning("dust3r_not_installed", message="dust3r module not found.")
            return

        if self.model is None:
            log.info("loading_dust3r", model=self.model_path)
            self.model = AsymmetricCroCo3DSeg.from_pretrained(self.model_path).to(self.device)
            self.model.eval()

    def reconstruct_from_images(self, image_paths: list[str], output_dir: str):
        """
        Takes a list of uncalibrated image paths and outputs a dense point cloud and camera poses.
        """
        self.load_model()
        if not self.model:
            return None

        log.info("processing_dust3r", num_images=len(image_paths))
        try:
            # Prepare images
            imgs = []
            for path in image_paths:
                img = Image.open(path).convert('RGB')
                imgs.append(dict(img=img, true_shape=np.array(img.size)[::-1], idx=len(imgs)))

            # Inference
            pairs = make_pairs(imgs, scene_graph='complete', prefilter=None, symmetrize=True)
            output = inference(pairs, self.model, self.device, batch_size=2)
            
            # Global Alignment
            scene = global_aligner(output, device=self.device, mode=GlobalAlignerMode.PointCloudOptimizer)
            loss = scene.compute_global_alignment(init="mst", niter=300, schedule='linear', lr=0.01)
            
            # Retrieve 3D point cloud
            pts3d = scene.get_pts3d()
            
            # Save results
            os.makedirs(output_dir, exist_ok=True)
            np.save(os.path.join(output_dir, "point_cloud.npy"), pts3d.detach().cpu().numpy())
            log.info("dust3r_reconstruction_complete", output_dir=output_dir)
            return output_dir
            
        except Exception as e:
            log.error("dust3r_error", error=str(e))
            return None
