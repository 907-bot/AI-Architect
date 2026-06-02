# AI Architect — Unreal Engine 5 Integration Roadmap

## Architecture Philosophy (from project brief)

```
AI Planner → TOON → Scene Graph → Blender → GLB → Unreal
```

Unreal is the SHOWROOM, not the brain.

| Component     | Role                              |
|---------------|-----------------------------------|
| AI + TOON     | Architectural intelligence        |
| Scene Graph   | Building blueprint (source of truth) |
| Blender       | Procedural construction factory   |
| Unreal Engine | Photoreal visualization + VR      |

## When to activate Unreal (checklist)

- [ ] Walkthrough — walk every room ✓ (done in Three.js)
- [ ] Interior generation — furniture per room ✓ (done)
- [ ] Room editing — "make bedroom larger" via scene graph
- [ ] Material customization — change floor/wall/furniture
- [ ] Floor plans — always generated ✓ (done)
- [ ] AI editing — natural language room edits
- [ ] Save/load projects
- [ ] Construction cost estimation ✓ (done)
- [ ] Sunlight analysis
→ THEN activate Unreal for photoreal presentations

## Pipeline (USD-based, production-grade)

```
Scene Graph (JSON)
      ↓
Blender Python Worker
      ↓
USD Export (Universal Scene Description)
      ↓
Unreal Datasmith USD Importer
      ↓
Nanite + Lumen + Path Tracing
      ↓
Movie Render Queue → 4K video / stills
      ↓
VR / XR (Meta Quest, Apple Vision Pro)
```

## USD vs GLB

| Format | Pros | Cons |
|--------|------|------|
| GLB    | Simple, works now | No USD metadata, no instancing |
| USD    | Full scene hierarchy, materials, lights, animation, instancing | Requires more setup |

Recommendation: Export BOTH. GLB for the web viewer, USD for Unreal.

## Blender → USD Export

```python
# In blender_worker.py — add alongside GLB export
bpy.ops.wm.usd_export(
    filepath=output_path.replace(".glb", ".usdc"),
    export_materials=True,
    export_lights=True,
    export_cameras=True,
    export_normals=True,
    export_uvmaps=True,
    export_mesh_colors=True,
    export_hair=False,
    use_instancing=True,
    evaluation_mode="RENDER",
)
```

## Unreal Auto-Import via Datasmith USD

```python
# ue5_setup.py extension — add USD import
import unreal

def import_usd(usd_path, destination):
    datasmith = unreal.DatasmithUSDImporter()
    # ... (see ue5_setup.py for full implementation)
```

## Feature Roadmap

### Phase 1 (Now — on blender-llama-integration branch)
- [x] Walkthrough (Three.js first-person)
- [x] Interior generation (furniture per room)
- [x] Floor plans always generated
- [x] 48 world architectural styles
- [x] NBC compliance + BOQ
- [ ] Room editing via AI ("make bedroom larger")
- [ ] Material customization panel
- [ ] Sunlight analysis (time-of-day slider)
- [ ] Save/load projects (localStorage + backend)

### Phase 2 (feature/unreal-engine branch — when Phase 1 complete)
- [ ] USD export alongside GLB
- [ ] Unreal auto-import via Datasmith
- [ ] Nanite + Lumen materials per room type
- [ ] Movie Render Queue integration
- [ ] Cinematic flythrough sequences
- [ ] Exterior + interior shots auto-generated

### Phase 3 (future)
- [ ] VR walkthrough (Meta Quest via Unreal)
- [ ] Multiplayer collaboration
- [ ] Digital twin foundation
- [ ] Construction sequence visualization
- [ ] IoT sensor overlay
