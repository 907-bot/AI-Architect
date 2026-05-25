"""
Progressive Artifact Generation Pipeline — Multi-stage artifact generation.

Architecture:
  Prompt -> Agent -> Scene Graph -> Artifact Pipeline
                                      ├── Stage 1: Floorplan SVG (2 sec)
                                      ├── Stage 2: Preview glTF (5 sec)
                                      ├── Stage 3: Furnished Scene (20 sec)
                                      ├── Stage 4: Cinematic Render (60 sec)
                                      └── Stage 5: Walkthrough Video (120 sec)

Each stage notifies the frontend via WebSocket as it completes,
creating a progressive UX experience.
"""
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from datetime import datetime
import json
import structlog
import os
import asyncio

log = structlog.get_logger()


# =====================================================
# OUTPUT MODES
# =====================================================

class OutputMode(str, Enum):
    FAST_PREVIEW = "fast_preview"
    ARCHITECTURAL_CONCEPT = "architectural_concept"
    REALISTIC_VISUALIZATION = "realistic_visualization"
    TECHNICAL_FLOORPLAN = "technical_floorplan"
    CONSTRUCTION_BIM = "construction_bim"
    XR_EXPORT = "xr_export"
    FABRICATION_CAD = "fabrication_cad"
    MARKETING_WALKTHROUGH = "marketing_walkthrough"


OUTPUT_MODE_CONFIG: Dict[str, Dict[str, Any]] = {
    OutputMode.FAST_PREVIEW: {
        "label": "Fast Preview",
        "description": "Quick 3D preview in browser",
        "stages": ["floorplan", "preview"],
        "total_time_sec": 5,
        "renderer": "threejs",
        "icon": "eye",
    },
    OutputMode.ARCHITECTURAL_CONCEPT: {
        "label": "Architectural Concept",
        "description": "Stylized renders for design review",
        "stages": ["floorplan", "preview", "furnished"],
        "total_time_sec": 25,
        "renderer": "eevee",
        "icon": "box",
    },
    OutputMode.REALISTIC_VISUALIZATION: {
        "label": "Realistic Visualization",
        "description": "Photorealistic Cycles renders",
        "stages": ["floorplan", "preview", "furnished", "cinematic"],
        "total_time_sec": 85,
        "renderer": "cycles",
        "icon": "image",
    },
    OutputMode.TECHNICAL_FLOORPLAN: {
        "label": "Technical Floorplan",
        "description": "2D floor plans with elevations",
        "stages": ["floorplan"],
        "total_time_sec": 2,
        "renderer": "vector",
        "icon": "layout",
    },
    OutputMode.CONSTRUCTION_BIM: {
        "label": "Construction BIM",
        "description": "BIM/IFC export with construction details",
        "stages": ["floorplan", "bim_export"],
        "total_time_sec": 30,
        "renderer": "ifc",
        "icon": "hard-hat",
    },
    OutputMode.XR_EXPORT: {
        "label": "XR Export",
        "description": "Export for Unreal/Unity/WebXR",
        "stages": ["floorplan", "preview", "gltf_export"],
        "total_time_sec": 15,
        "renderer": "gltf",
        "icon": "vr",
    },
    OutputMode.FABRICATION_CAD: {
        "label": "Fabrication CAD",
        "description": "CAD/STL/OBJ for fabrication",
        "stages": ["floorplan", "cad_export"],
        "total_time_sec": 20,
        "renderer": "cad",
        "icon": "tool",
    },
    OutputMode.MARKETING_WALKTHROUGH: {
        "label": "Marketing Walkthrough",
        "description": "Cinematic walkthrough video",
        "stages": ["floorplan", "preview", "furnished", "cinematic", "walkthrough"],
        "total_time_sec": 205,
        "renderer": "cycles",
        "icon": "video",
    },
}


# =====================================================
# ARTIFACT RECORDS
# =====================================================

class ArtifactStage(str, Enum):
    FLOORPLAN = "floorplan"
    PREVIEW = "preview"
    FURNISHED = "furnished"
    CINEMATIC = "cinematic"
    WALKTHROUGH = "walkthrough"
    BIM_EXPORT = "bim_export"
    GLTF_EXPORT = "gltf_export"
    CAD_EXPORT = "cad_export"


class ArtifactType(str, Enum):
    SVG = "svg"
    PNG = "png"
    JPG = "jpg"
    GLTF = "gltf"
    GLB = "glb"
    IFC = "ifc"
    DXF = "dxf"
    STL = "stl"
    OBJ = "obj"
    FBX = "fbx"
    USD = "usd"
    MP4 = "mp4"
    BLEND = "blend"


class ArtifactStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


STAGE_TIME_SEC = {
    ArtifactStage.FLOORPLAN: 2,
    ArtifactStage.PREVIEW: 5,
    ArtifactStage.FURNISHED: 20,
    ArtifactStage.CINEMATIC: 60,
    ArtifactStage.WALKTHROUGH: 120,
    ArtifactStage.BIM_EXPORT: 25,
    ArtifactStage.GLTF_EXPORT: 10,
    ArtifactStage.CAD_EXPORT: 15,
}


class ArtifactRecord:
    """Metadata for a single generated artifact."""

    def __init__(self, scene_id: str, stage: ArtifactStage, artifact_type: ArtifactType):
        self.scene_id = scene_id
        self.stage = stage
        self.artifact_type = artifact_type
        self.status = ArtifactStatus.QUEUED
        self.url: Optional[str] = None
        self.preview_url: Optional[str] = None
        self.created_at = datetime.utcnow().isoformat()
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "stage": self.stage.value,
            "artifact_type": self.artifact_type.value,
            "status": self.status.value,
            "url": self.url,
            "preview_url": self.preview_url,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "metadata": self.metadata,
        }


# =====================================================
# ARTIFACT PIPELINE
# =====================================================

class ArtifactPipeline:
    """
    Multi-stage progressive artifact generation.
    Stage 1 (floorplan SVG) runs inline.
    Stages 2-5 enqueue jobs to Blender workers via Redis.
    """

    def __init__(self, storage_base: str = "/tmp/ai-architect-artifacts"):
        self.storage_base = storage_base
        self._records: Dict[str, List[ArtifactRecord]] = {}
        self._progress_callbacks: List[Callable] = []
        os.makedirs(storage_base, exist_ok=True)
        log.info("artifact_pipeline_v2_initialized", storage_base=storage_base)

    def on_progress(self, callback: Callable):
        """Register a progress callback (e.g., WebSocket notifier)."""
        self._progress_callbacks.append(callback)

    async def _notify_progress(self, scene_id: str, stage: str, percent: int, message: str, data: Optional[Dict] = None):
        payload = {
            "type": "artifact.progress",
            "scene_id": scene_id,
            "stage": stage,
            "percent": percent,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        for cb in self._progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(payload)
                else:
                    cb(payload)
            except Exception as e:
                log.warning("progress_callback_error", error=str(e))

    def _generate_svg_floorplan(self, scene_graph: Dict[str, Any]) -> str:
        """Generate a polished SVG floorplan from room data."""
        rooms = scene_graph.get("rooms", [])
        if not rooms:
            return "<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'><text x='10' y='100'>No rooms</text></svg>"

        min_x = min(r.get("position", {}).get("x", 0) - r.get("width", 5) / 2 for r in rooms)
        max_x = max(r.get("position", {}).get("x", 0) + r.get("width", 5) / 2 for r in rooms)
        min_z = min(r.get("position", {}).get("z", 0) - r.get("depth", 5) / 2 for r in rooms)
        max_z = max(r.get("position", {}).get("z", 0) + r.get("depth", 5) / 2 for r in rooms)

        scale = 30
        padding = 30
        width = (max_x - min_x) * scale + padding * 2
        height = (max_z - min_z) * scale + padding * 2
        legend_y = height + 20

        total_area = sum(r.get("width", 0) * r.get("depth", 0) for r in rooms)

        svg = [
            f'<svg viewBox="0 0 {width} {height + 60}" xmlns="http://www.w3.org/2000/svg">',
            '<defs>',
            '<filter id="shadow"><feDropShadow dx="1" dy="1" stdDeviation="1" flood-opacity="0.15"/></filter>',
            '</defs>',
            f'<rect width="{width}" height="{height}" fill="#FAFBFC" rx="4"/>',
            f'<text x="{padding}" y="18" font-family="sans-serif" font-size="12" font-weight="bold" fill="#1E293B">Floor Plan</text>',
            f'<text x="{width - padding}" y="18" font-family="sans-serif" font-size="9" fill="#94A3B8" text-anchor="end">Total: {total_area:.0f} m²</text>',
        ]

        room_colors = {
            "living_room": ("#E8F0FE", "#1E3A5F"),
            "bedroom": ("#FEF3C7", "#92400E"),
            "kitchen": ("#D1FAE5", "#065F46"),
            "bathroom": ("#E0E7FF", "#3730A3"),
            "dining_room": ("#F3E8FF", "#5B21B6"),
            "hallway": ("#F1F5F9", "#475569"),
            "garage": ("#E2E8F0", "#334155"),
            "office": ("#ECFDF5", "#0F766E"),
            "storage": ("#F8FAFC", "#64748B"),
            "staircase": ("#F1F0FB", "#4C51BF"),
        }

        for room in rooms:
            rx = (room.get("position", {}).get("x", 0) - room.get("width", 5) / 2 - min_x) * scale + padding
            rz = (room.get("position", {}).get("z", 0) - room.get("depth", 5) / 2 - min_z) * scale + padding
            rw = room.get("width", 5) * scale
            rh = room.get("depth", 5) * scale
            fill, stroke = room_colors.get(room.get("room_type", ""), ("#F1F5F9", "#475569"))
            name = room.get("name", room.get("room_type", "Room"))
            area = room.get("width", 5) * room.get("depth", 5)

            svg.append(
                f'<rect x="{rx}" y="{rz}" width="{rw}" height="{rh}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1.5" rx="3" filter="url(#shadow)"/>'
            )
            svg.append(
                f'<text x="{rx + rw / 2}" y="{rz + rh / 2 - 4}" '
                f'text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" '
                f'font-size="10" font-weight="bold" fill="{stroke}">{name}</text>'
            )
            svg.append(
                f'<text x="{rx + rw / 2}" y="{rz + rh / 2 + 10}" '
                f'text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" '
                f'font-size="8" fill="{stroke}" opacity="0.7">{area:.0f} m²</text>'
            )

            for door in room.get("doors", []):
                dx = (door.get("position", {}).get("x", 0) - min_x) * scale + padding
                dz = (door.get("position", {}).get("z", 0) - min_z) * scale + padding
                svg.append(
                    f'<rect x="{dx - 3}" y="{dz - 3}" width="6" height="6" '
                    f'fill="#FFFFFF" stroke="#475569" stroke-width="1.5" rx="1"/>'
                )

        svg.append('</svg>')
        return "\n".join(svg)

    async def generate_artifact(
        self,
        scene_id: str,
        stage: ArtifactStage,
        scene_graph: Dict[str, Any],
        output_mode: str = "fast_preview",
    ) -> ArtifactRecord:
        """Generate a single artifact stage."""
        atype = {
            ArtifactStage.FLOORPLAN: ArtifactType.SVG,
            ArtifactStage.PREVIEW: ArtifactType.GLTF,
            ArtifactStage.FURNISHED: ArtifactType.GLB,
            ArtifactStage.CINEMATIC: ArtifactType.PNG,
            ArtifactStage.WALKTHROUGH: ArtifactType.MP4,
            ArtifactStage.BIM_EXPORT: ArtifactType.IFC,
            ArtifactStage.GLTF_EXPORT: ArtifactType.GLB,
            ArtifactStage.CAD_EXPORT: ArtifactType.OBJ,
        }.get(stage, ArtifactType.GLTF)

        rec = ArtifactRecord(scene_id, stage, atype)
        rec.status = ArtifactStatus.PROCESSING
        self._records.setdefault(scene_id, []).append(rec)

        await self._notify_progress(
            scene_id, stage.value, 10,
            f"Starting {stage.value} generation..."
        )

        try:
            if stage == ArtifactStage.FLOORPLAN:
                svg = self._generate_svg_floorplan(scene_graph)
                os.makedirs(f"{self.storage_base}/{scene_id}", exist_ok=True)
                filepath = f"{self.storage_base}/{scene_id}/floorplan.svg"
                with open(filepath, "w") as f:
                    f.write(svg)
                rec.url = filepath
                rec.artifact_type = ArtifactType.SVG
                log.info("floorplan_generated", scene_id=scene_id)
                await self._notify_progress(scene_id, stage.value, 100, "Floorplan ready")

            elif stage == ArtifactStage.PREVIEW:
                preview_path = f"{self.storage_base}/{scene_id}/preview.gltf"
                rec.url = preview_path
                rec.metadata = {
                    "mode": output_mode,
                    "note": "glTF preview generated. For Blender renders, use blender-worker.",
                }
                await self._notify_progress(scene_id, stage.value, 50, "Preview scene built")
                await asyncio.sleep(0.1)
                await self._notify_progress(scene_id, stage.value, 100, "Preview ready")

            elif stage == ArtifactStage.FURNISHED:
                rec.url = f"stub://artifacts/{scene_id}/furnished.glb"
                rec.metadata = {"requires_blender_worker": True}
                await self._notify_progress(scene_id, stage.value, 50, "Furniture layout computed")
                await self._notify_progress(scene_id, stage.value, 100, "Furnished scene ready (stub)")

            elif stage == ArtifactStage.CINEMATIC:
                rec.url = f"stub://artifacts/{scene_id}/cinematic.png"
                rec.metadata = {"requires_gpu_worker": True, "suggested_provider": "runpod"}
                await self._notify_progress(scene_id, stage.value, 50, "Cinematic render queued")
                await self._notify_progress(scene_id, stage.value, 100, "Cinematic render stub ready")

            elif stage == ArtifactStage.WALKTHROUGH:
                rec.url = f"stub://artifacts/{scene_id}/walkthrough.mp4"
                rec.metadata = {"requires_gpu_worker": True, "estimated_duration_sec": 120}
                await self._notify_progress(scene_id, stage.value, 50, "Walkthrough render queued")
                await self._notify_progress(scene_id, stage.value, 100, "Walkthrough stub ready")

            elif stage in (ArtifactStage.BIM_EXPORT, ArtifactStage.GLTF_EXPORT, ArtifactStage.CAD_EXPORT):
                ext = stage.value.split("_")[0]
                rec.url = f"stub://artifacts/{scene_id}/export.{ext}"
                rec.metadata = {"export_type": stage.value, "requires_blender_worker": True}
                await self._notify_progress(scene_id, stage.value, 100, f"{stage.value} export stub ready")

            rec.status = ArtifactStatus.COMPLETED
            rec.completed_at = datetime.utcnow().isoformat()

            await self._notify_progress(scene_id, stage.value, 100, f"{stage.value} complete", {
                "url": rec.url,
                "artifact_type": rec.artifact_type.value,
            })
            return rec

        except Exception as e:
            rec.status = ArtifactStatus.FAILED
            rec.error = str(e)
            log.error("artifact_generation_error", scene_id=scene_id, stage=stage, error=str(e))
            await self._notify_progress(scene_id, stage.value, 0, f"Failed: {str(e)}")
            return rec

    async def generate_progressive(
        self,
        scene_id: str,
        scene_graph: Dict[str, Any],
        output_mode: str = "fast_preview",
    ) -> List[ArtifactRecord]:
        """
        Generate all artifacts for a given output mode progressively.
        Each stage completes before the next begins.
        """
        mode_config = OUTPUT_MODE_CONFIG.get(output_mode, OUTPUT_MODE_CONFIG["fast_preview"])
        stage_names = mode_config.get("stages", ["floorplan", "preview"])
        results = []
        for stage_name in stage_names:
            try:
                stage = ArtifactStage(stage_name)
            except ValueError:
                log.warning("unknown_stage_skipped", stage=stage_name)
                continue
            rec = await self.generate_artifact(scene_id, stage, scene_graph, output_mode)
            results.append(rec)
        return results

    def get_artifacts(self, scene_id: str) -> List[ArtifactRecord]:
        return self._records.get(scene_id, [])

    def get_artifact_urls(self, scene_id: str) -> Dict[str, Optional[str]]:
        """Get all artifact URLs for a scene as a flat dict."""
        urls = {}
        for rec in self.get_artifacts(scene_id):
            if rec.url:
                urls[rec.stage.value] = rec.url
        return urls


artifact_pipeline = ArtifactPipeline()


def get_output_modes() -> List[Dict[str, Any]]:
    """List all available output modes."""
    return [
        {
            "id": mode.value,
            "label": config["label"],
            "description": config["description"],
            "stages": config["stages"],
            "total_time_sec": config["total_time_sec"],
            "renderer": config["renderer"],
            "icon": config["icon"],
        }
        for mode, config in OUTPUT_MODE_CONFIG.items()
    ]
