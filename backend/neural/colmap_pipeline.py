"""
COLMAP Pipeline - Structure from Motion (SfM)
Calculates exact camera poses required before generating Gaussian Splats.
"""
import subprocess
import os
import structlog

log = structlog.get_logger()

class ColmapPipeline:
    def __init__(self, colmap_executable="colmap"):
        self.colmap = colmap_executable

    def run_sfm(self, image_dir: str, workspace_dir: str) -> bool:
        """
        Runs the full COLMAP Structure from Motion pipeline automatically.
        """
        os.makedirs(workspace_dir, exist_ok=True)
        database_path = os.path.join(workspace_dir, "database.db")
        
        log.info("colmap_starting", image_dir=image_dir, workspace=workspace_dir)

        try:
            # 1. Feature extraction
            subprocess.run([
                self.colmap, "feature_extractor",
                "--database_path", database_path,
                "--image_path", image_dir,
                "--ImageReader.single_camera", "1"
            ], check=True, capture_output=True)
            
            # 2. Exhaustive matcher
            subprocess.run([
                self.colmap, "exhaustive_matcher",
                "--database_path", database_path
            ], check=True, capture_output=True)
            
            # 3. Mapper (SfM)
            sparse_dir = os.path.join(workspace_dir, "sparse")
            os.makedirs(sparse_dir, exist_ok=True)
            
            subprocess.run([
                self.colmap, "mapper",
                "--database_path", database_path,
                "--image_path", image_dir,
                "--output_path", sparse_dir
            ], check=True, capture_output=True)
            
            log.info("colmap_completed_successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            log.error("colmap_failed", error=e.stderr.decode('utf-8'))
            return False
