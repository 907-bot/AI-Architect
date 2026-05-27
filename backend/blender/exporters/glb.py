from __future__ import annotations

from pathlib import Path


def export_glb(output_path: str | Path) -> str:
    try:
        import bpy
    except ImportError as exc:
        raise RuntimeError("bpy is only available when running inside Blender") from exc

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB")
    return str(path)
