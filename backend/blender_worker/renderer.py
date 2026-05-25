"""
Blender Renderer — Renders artifacts from built Blender scenes.
Supports Eevee (fast) and Cycles (cinematic) render engines.
"""
from typing import Optional, Dict, Any
import structlog
import os
import json

log = structlog.get_logger()


class BlenderRenderer:
    """
    Renders Blender scenes to various output formats.
    Requires bpy (Blender Python API).
    """

    RENDER_PRESETS = {
        "preview": {
            "engine": "BLENDER_EEVEE",
            "samples": 32,
            "resolution_x": 1280,
            "resolution_y": 720,
            "use_denoising": False,
        },
        "medium": {
            "engine": "BLENDER_EEVEE",
            "samples": 128,
            "resolution_x": 1920,
            "resolution_y": 1080,
            "use_denoising": True,
        },
        "cinematic": {
            "engine": "CYCLES",
            "samples": 512,
            "resolution_x": 3840,
            "resolution_y": 2160,
            "use_denoising": True,
        },
        "production": {
            "engine": "CYCLES",
            "samples": 2048,
            "resolution_x": 7680,
            "resolution_y": 4320,
            "use_denoising": True,
        },
    }

    def __init__(self, preset: str = "medium"):
        self.preset = preset
        self._bpy = None
        self._try_import_bpy()

    def _try_import_bpy(self):
        try:
            import bpy
            self._bpy = bpy
        except ImportError:
            pass

    def _has_bpy(self) -> bool:
        return self._bpy is not None

    def configure_scene(self, preset: Optional[str] = None):
        """Configure render settings for the scene."""
        if not self._has_bpy():
            return

        bpy = self._bpy
        preset_name = preset or self.preset
        config = self.RENDER_PRESETS.get(preset_name, self.RENDER_PRESETS["medium"])

        scene = bpy.context.scene
        scene.render.engine = config["engine"]
        scene.render.resolution_x = config["resolution_x"]
        scene.render.resolution_y = config["resolution_y"]

        if config["engine"] == "CYCLES":
            scene.cycles.samples = config["samples"]
            if config["use_denoising"]:
                scene.cycles.use_denoising = True

        bpy.context.view_layer.update()
        log.info("render_configured", preset=preset_name, engine=config["engine"])

    def render_still(self, output_path: str, camera_name: Optional[str] = None) -> str:
        """Render a single still image."""
        if not self._has_bpy():
            log.warning("cannot_render_no_blender")
            return "stub://render/no_blender_available.png"

        bpy = self._bpy
        if camera_name and camera_name in bpy.data.objects:
            bpy.context.scene.camera = bpy.data.objects[camera_name]
        elif bpy.data.objects.get("Camera"):
            bpy.context.scene.camera = bpy.data.objects["Camera"]

        bpy.context.scene.render.filepath = output_path
        bpy.ops.render.render(write_still=True)
        log.info("still_rendered", path=output_path)
        return output_path

    def render_walkthrough(
        self,
        output_path: str,
        camera_path: list,
        duration_sec: int = 30,
        fps: int = 24,
    ) -> str:
        """Render a walkthrough animation along a camera path."""
        if not self._has_bpy():
            return "stub://render/walkthrough_stub.mp4"

        bpy = self._bpy
        total_frames = duration_sec * fps

        scene = bpy.context.scene
        scene.frame_start = 1
        scene.frame_end = total_frames
        scene.render.filepath = output_path
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"

        for i, point in enumerate(camera_path):
            frame = int((i / len(camera_path)) * total_frames)
            if frame < 1:
                frame = 1
            loc = point.get("location", (0, 0, 0))
            target = point.get("target", (0, 0, 0))
            bpy.context.scene.frame_set(frame)
            if bpy.data.objects.get("Camera"):
                cam = bpy.data.objects["Camera"]
                cam.location = loc
                direction = (
                    target[0] - loc[0],
                    target[1] - loc[1],
                    target[2] - loc[2],
                )
                cam.rotation_euler = (
                    direction[1],
                    direction[0],
                    direction[2],
                )
                cam.keyframe_insert(data_path="location", index=-1)
                cam.keyframe_insert(data_path="rotation_euler", index=-1)

        bpy.ops.render.render(animation=True)
        log.info("walkthrough_rendered", path=output_path, frames=total_frames)
        return output_path

    def export_gltf(self, output_path: str) -> str:
        """Export scene as glTF."""
        if not self._has_bpy():
            return "stub://export/gltf_stub.glb"

        bpy = self._bpy
        bpy.ops.export_scene.gltf(
            filepath=output_path,
            export_format="GLB",
            export_draco_mesh_compression_enable=True,
            export_apply=True,
        )
        log.info("gltf_exported", path=output_path)
        return output_path

    def export_ifc(self, output_path: str) -> str:
        """Export scene as IFC (requires IfcOpenShell)."""
        return "stub://export/ifc_stub.ifc"

    def export_obj(self, output_path: str) -> str:
        """Export scene as OBJ."""
        if not self._has_bpy():
            return "stub://export/obj_stub.obj"

        bpy = self._bpy
        bpy.ops.export_scene.obj(
            filepath=output_path,
            use_selection=False,
        )
        log.info("obj_exported", path=output_path)
        return output_path

    def render_floorplan(self, output_path: str) -> str:
        """Render a top-down orthographic floorplan."""
        if not self._has_bpy():
            return "stub://export/floorplan_stub.png"

        bpy = self._bpy
        if bpy.data.objects.get("Top_View"):
            bpy.context.scene.camera = bpy.data.objects["Top_View"]
        scene = bpy.context.scene
        scene.render.resolution_x = 1920
        scene.render.resolution_y = 1080
        scene.render.filepath = output_path
        bpy.ops.render.render(write_still=True)
        return output_path
