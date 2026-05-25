"""
Tests for progressive artifact generation pipeline.
"""
import pytest
from backend.services.artifacts import (
    ArtifactPipeline, ArtifactStage, ArtifactStatus, ArtifactType
)


@pytest.fixture
def pipeline():
    return ArtifactPipeline(storage_base="/tmp/test_artifacts")


def test_floorplan_svg_generation(pipeline):
    scene_graph = {
        "rooms": [
            {
                "id": "lr",
                "room_type": "living_room",
                "name": "Living Room",
                "position": {"x": 0, "y": 0, "z": 0},
                "width": 6.0,
                "depth": 5.0,
            },
            {
                "id": "br",
                "room_type": "bedroom",
                "name": "Bedroom",
                "position": {"x": 0, "y": 0, "z": 6},
                "width": 5.0,
                "depth": 4.0,
            },
        ]
    }

    svg = pipeline._generate_svg_floorplan(scene_graph)
    assert "<svg" in svg
    assert "Living Room" in svg
    assert "Bedroom" in svg
    assert "</svg>" in svg


def test_floorplan_empty_rooms(pipeline):
    svg = pipeline._generate_svg_floorplan({"rooms": []})
    assert "No rooms" in svg


@pytest.mark.asyncio
async def test_generate_floorplan_artifact(pipeline):
    result = await pipeline.generate_artifact(
        scene_id="test_scene_001",
        stage=ArtifactStage.FLOORPLAN,
        scene_graph={
            "rooms": [{
                "id": "r1", "room_type": "kitchen", "name": "Kitchen",
                "position": {"x": 0, "y": 0, "z": 0},
                "width": 4.0, "depth": 4.0,
            }]
        }
    )
    assert result.stage == ArtifactStage.FLOORPLAN
    assert result.status == ArtifactStatus.COMPLETED
    assert result.artifact_type == ArtifactType.SVG
    assert result.url is not None
    assert "floorplan.svg" in result.url


@pytest.mark.asyncio
async def test_generate_preview_stub(pipeline):
    result = await pipeline.generate_artifact(
        scene_id="test_scene_002",
        stage=ArtifactStage.PREVIEW,
        scene_graph={"rooms": []}
    )
    assert result.stage == ArtifactStage.PREVIEW
    assert result.status == ArtifactStatus.COMPLETED
    assert "stub://" in result.url


def test_get_artifacts(pipeline):
    # Pipeline not yet tracked for this scene
    artifacts = pipeline.get_artifacts("nonexistent")
    assert artifacts == []
