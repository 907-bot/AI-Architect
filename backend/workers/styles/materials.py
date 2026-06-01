"""
backend/workers/styles/materials.py
====================================
Centralized, photorealistic per-style material palette registry.

Each entry in STYLE_PALETTES maps a style name to a flat dictionary of
``slot → (R, G, B)`` tuples (linear sRGB, 0–1 range, as expected by Blender's
Principled BSDF).  Additional scalar keys control roughness, metalness, alpha
and special behaviour flags.

The ``get_palette(style_name)`` helper returns the merged palette for a given
style, falling back to ``"modern"`` for unknown names.

Usage (inside blender_worker.py, which runs inside Blender):
    from styles.materials import get_palette, get_lighting_config
    palette = get_palette("japanese")
"""

from __future__ import annotations
from typing import Any, Dict

# ─────────────────────────────────────────────────────────────────────────────
# Type alias
# ─────────────────────────────────────────────────────────────────────────────
RGB   = tuple[float, float, float]
Slot  = str
Pal   = Dict[str, Any]   # palette dict: slot → RGB | float | bool


# ─────────────────────────────────────────────────────────────────────────────
# Helper: convert hex string "#RRGGBB" → linear-sRGB (R,G,B) floats
# Blender materials expect linear colour space, so we apply gamma-decode.
# ─────────────────────────────────────────────────────────────────────────────
def _hex(h: str) -> RGB:
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    def lin(c: int) -> float:
        v = c / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (lin(r), lin(g), lin(b))


# ─────────────────────────────────────────────────────────────────────────────
# BASE / FALLBACK palette  (used as default when a style omits a slot)
# ─────────────────────────────────────────────────────────────────────────────
_BASE: Pal = {
    # Structural
    "wall":           _hex("#D1CBC0"),
    "wall_rough":     0.85,
    "wall_bump":      0.50,
    "wall_brick":     _hex("#9E7A66"),
    "slab":           _hex("#B8B4AE"),
    "concrete":       _hex("#9E9A94"),
    "facade":         _hex("#C8C4BC"),
    # Roof
    "roof":           _hex("#3D3D3D"),
    "roof_rough":     0.70,
    "roof_bump":      0.40,
    "roof_tile":      _hex("#3D3D3D"),
    "roof_metal":     _hex("#3D3D3D"),
    # Glass & metal
    "glass":          _hex("#B8E0F7"),
    "glass_alpha":    0.12,
    "glass_rough":    0.02,
    "frame":          _hex("#141416"),
    "frame_metal":    0.90,
    "steel":          _hex("#A5A5A8"),
    # Accent
    "accent":         _hex("#406CA5"),
    "column":         _hex("#D1CBC0"),
    "wood_dark":      _hex("#472D20"),
    "wood_light":     _hex("#9E7245"),
    # Ground / landscape
    "ground":         _hex("#332E24"),
    "grass":          _hex("#2E7326"),
    "pavement":       _hex("#99958A"),
    "gravel":         _hex("#7A7670"),
    "asphalt":        _hex("#1F1F21"),
    "sand":           _hex("#C6B88C"),
    "path":           _hex("#A69F96"),
    # Water
    "pool_water":     _hex("#0A85C8"),
    "pool_water_alpha": 0.65,
    "pool_water_trans": 0.85,
    "pool_tile":      _hex("#C8E6F2"),
    "water":          _hex("#0D6699"),
    "water_alpha":    0.55,
    "water_trans":    0.88,
    # Nature
    "bark":           _hex("#4D3320"),
    "foliage_a":      _hex("#2E7326"),
    "foliage_b":      _hex("#245C1E"),
    "foliage_dark":   _hex("#0F471A"),
    # Special mats
    "shoji":          _hex("#F2EDE4"),   # warm translucent paper
    "shoji_alpha":    0.70,
    "bamboo":         _hex("#B8C761"),
    "tatami":         _hex("#B8AE6B"),
    "stone_zen":      _hex("#858480"),
    "terracotta":     _hex("#B36138"),
    "plaster":        _hex("#D1CBC0"),
    "marble":         _hex("#EBEAE8"),
    "white_paint":    _hex("#F2F0ED"),
    "brick_red":      _hex("#9E4730"),
    "corten":         _hex("#853D26"),
    "corrugated":     _hex("#7A7A80"),
    "exposed_conc":   _hex("#8C8A85"),
    "door":           _hex("#141416"),
    # Interior
    "interior_floor": _hex("#9E7245"),   # default: wood_light
    "interior_wall":  _hex("#E8DDD0"),
    "interior_ceil":  _hex("#F2F0ED"),
    "sofa":           _hex("#7A6E6A"),
    "cushion_accent": _hex("#406CA5"),
    "table_top":      _hex("#9E7245"),
    "lantern":        None,              # None → no emission
    "lantern_color":  _hex("#F4C842"),
}


# ─────────────────────────────────────────────────────────────────────────────
# JAPANESE ZEN  — Golden-hour warm amber + cool violet shadows, wabi-sabi
# Reference palette from designer session (2026-06-01)
# ─────────────────────────────────────────────────────────────────────────────
_JAPANESE: Pal = {
    # ── Exterior ──────────────────────────────────────────────────────────────
    "wall":           _hex("#F2EDE4"),  # Warm Washi White (aged plaster)
    "wall_rough":     0.82,
    "wall_bump":      0.40,
    "wall_wood":      _hex("#4A2C2A"),  # Dark Persimmon Wood (hinoki/sugi cedar)
    "wall_brick":     _hex("#C4A882"),  # Raw Terracotta Sand (garden wall)
    "facade":         _hex("#F2EDE4"),
    "slab":           _hex("#5C5850"),  # Sumi Stone — foundation/base
    "concrete":       _hex("#5C5850"),
    "roof":           _hex("#2E2E2E"),  # Deep Charcoal Slate (kawara clay tile)
    "roof_rough":     0.75,
    "roof_bump":      0.50,
    "roof_tile":      _hex("#2E2E2E"),
    "roof_metal":     _hex("#6B5C3E"),  # Aged Bronze ridge
    "accent":         _hex("#6B5C3E"),  # Aged Bronze
    "frame":          _hex("#C8A97B"),  # Natural Bamboo (shoji lattice)
    "frame_metal":    0.0,              # pure wood, no metalness
    "column":         _hex("#4A2C2A"),  # Dark Persimmon Wood — distinct from wall
    "wood_dark":      _hex("#4A2C2A"),  # Dark Persimmon Wood
    "wood_light":     _hex("#B8824E"),  # Aged Hinoki Cedar (engawa floor)
    # ── Glass / screens ───────────────────────────────────────────────────────
    "glass":          _hex("#E6F0E2"),  # Translucent Silk (warm shoji paper glow)
    "glass_alpha":    0.30,
    "glass_rough":    0.05,
    "shoji":          _hex("#F5F0E8"),  # Translucent Silk — shoji screen panels
    "shoji_alpha":    0.65,
    # ── Ground / hardscape ───────────────────────────────────────────────────
    "ground":         _hex("#38302A"),  # Dark warm soil
    "grass":          _hex("#1E6119"),  # Deep Forest Moss
    "pavement":       _hex("#C8A97B"),  # Sand / gravel approach
    "gravel":         _hex("#C0BDB5"),  # Silver Pebble (raked zen garden)
    "sand":           _hex("#C8A97B"),  # Garden stepping-stone approach
    "path":           _hex("#A69688"),
    # ── Water / koi pond ─────────────────────────────────────────────────────
    "pool_water":     _hex("#4A7D6A"),  # Mossy Jade koi pond
    "pool_water_alpha": 0.55,
    "pool_water_trans": 0.82,
    "pool_tile":      _hex("#3D6B5C"),  # Deep teal pond floor
    "water":          _hex("#4A7D6A"),
    "water_alpha":    0.55,
    "water_trans":    0.82,
    # ── Nature ───────────────────────────────────────────────────────────────
    "foliage_a":      _hex("#5B7A3D"),  # Deep Forest Moss
    "foliage_b":      _hex("#8FAF44"),  # Fresh Bamboo green
    "foliage_dark":   _hex("#2E4D1A"),
    "bark":           _hex("#4D3320"),
    "bamboo":         _hex("#8FAF44"),  # Yellow-Green Bamboo
    "stone_zen":      _hex("#C0BDB5"),  # Silver Pebble stepping stones
    # ── Interior ─────────────────────────────────────────────────────────────
    "tatami":         _hex("#9CAF88"),  # Fresh Tatami Green (pale olive-green)
    "interior_floor": _hex("#9CAF88"),  # Tatami mats on floor surface
    "interior_wall":  _hex("#E8DDD0"),  # Warm Clay Plaster
    "interior_ceil":  _hex("#3B2A1E"),  # Dark Wenge Brown (exposed ceiling beams)
    "sofa":           _hex("#2A3A5C"),  # Indigo Shibori cushion (zabuton)
    "cushion_accent": _hex("#2A3A5C"),  # Indigo Shibori
    "table_top":      _hex("#B8824E"),  # Hinoki Cedar low table (chabudai)
    # ── Lantern emission ─────────────────────────────────────────────────────
    "lantern":        True,             # enable washi lantern glow
    "lantern_color":  _hex("#F4C842"),  # Candlelight Amber
    # ── Lighting overrides (used in setup_lighting) ───────────────────────────
    "sky_turbidity":  1.5,
    "sun_energy":     4.5,
    "sun_color":      _hex("#FFC47A"),  # Pale Dawn Orange
    "fill_energy":    280,
    "fill_color":     _hex("#FDEBBF"),  # Golden-hour warm fill
    "shadow_color":   _hex("#8090A8"),  # Cool Blue-Violet mist shadows
    "sun_elevation":  15.0,             # Low golden-hour sun angle (degrees)
    "sun_rotation":   215.0,
    "ambient_strength": 1.1,
    "fog":            True,
    "fog_color":      _hex("#D0D8E0"),  # Morning mist
    "fog_density":    0.08,
}

# ─────────────────────────────────────────────────────────────────────────────
# ITALIAN / MEDITERRANEAN VILLA  — Warm terracotta, plaster, deep greens
# ─────────────────────────────────────────────────────────────────────────────
_VILLA: Pal = {
    "wall":           _hex("#EDE0CC"),  # Aged warm plaster — ochre-cream
    "wall_rough":     0.88,
    "wall_bump":      0.45,
    "wall_wood":      _hex("#8C6240"),  # Walnut shutters
    "wall_brick":     _hex("#B8866A"),  # Warm sandstone
    "facade":         _hex("#EDE0CC"),
    "slab":           _hex("#C8BAA0"),  # Limestone
    "concrete":       _hex("#C8BAA0"),
    "roof":           _hex("#A64E2A"),  # Terracotta clay tile — rich burnt orange
    "roof_rough":     0.75,
    "roof_bump":      0.60,
    "roof_tile":      _hex("#A64E2A"),
    "roof_metal":     _hex("#7A5C3A"),
    "accent":         _hex("#B38A1A"),  # Warm gold ornament
    "frame":          _hex("#8A6A4A"),  # Warm brown — darker than wall for contrast
    "frame_metal":    0.10,
    "column":         _hex("#C8A87A"),  # Warm sand stone — distinct from plaster wall
    "wood_dark":      _hex("#5C3A1E"),
    "wood_light":     _hex("#A87840"),
    "glass":          _hex("#C8E6BF"),  # Warm green-tinted glass
    "glass_alpha":    0.18,
    "glass_rough":    0.03,
    "ground":         _hex("#473D2A"),
    "grass":          _hex("#38591A"),
    "pavement":       _hex("#C8B896"),  # Travertine courtyard
    "gravel":         _hex("#C0B898"),
    "sand":           _hex("#C8B896"),
    "path":           _hex("#B8A880"),
    "pool_water":     _hex("#0D91C8"),  # Vivid Mediterranean pool blue
    "pool_water_alpha": 0.60,
    "pool_water_trans": 0.90,
    "pool_tile":      _hex("#7EC8E3"),  # Azure pool tile
    "water":          _hex("#0D91C8"),
    "water_alpha":    0.60,
    "water_trans":    0.90,
    "foliage_a":      _hex("#38591A"),
    "foliage_b":      _hex("#2E471A"),
    "foliage_dark":   _hex("#1A3310"),
    "bark":           _hex("#5C3A1E"),
    "terracotta":     _hex("#B36138"),
    "plaster":        _hex("#EDE0CC"),
    "marble":         _hex("#EEECE8"),
    "interior_floor": _hex("#C8B080"),  # Warm terracotta floor tile
    "interior_wall":  _hex("#EDE0CC"),  # Aged plaster
    "interior_ceil":  _hex("#EEECE8"),  # White marble effect
    "sofa":           _hex("#8C6038"),  # Warm cognac leather
    "cushion_accent": _hex("#B38A1A"),  # Gold cushions
    "table_top":      _hex("#A87840"),
    "lantern":        True,
    "lantern_color":  _hex("#F0A830"),  # Warm candle flame
    "sky_turbidity":  2.0,
    "sun_energy":     5.5,
    "sun_color":      _hex("#FFE0A0"),  # Warm Mediterranean noon
    "fill_energy":    340,
    "fill_color":     _hex("#FFF5E0"),
    "shadow_color":   _hex("#5A7090"),
    "sun_elevation":  50.0,
    "sun_rotation":   200.0,
    "ambient_strength": 1.4,
    "fog":            False,
}

# ─────────────────────────────────────────────────────────────────────────────
# SCANDINAVIAN  — Crisp whites, light oak, charcoal accents, hygge warmth
# ─────────────────────────────────────────────────────────────────────────────
_SCANDINAVIAN: Pal = {
    "wall":           _hex("#F2F0ED"),  # Pure Nordic white
    "wall_rough":     0.80,
    "wall_bump":      0.35,
    "wall_wood":      _hex("#D2B48C"),  # Light birch cladding
    "wall_brick":     _hex("#A0948A"),  # Light grey stone
    "facade":         _hex("#F2F0ED"),
    "slab":           _hex("#B8B4AE"),
    "concrete":       _hex("#B0ACA6"),
    "roof":           _hex("#2E2E30"),  # Dark charcoal roof
    "roof_rough":     0.85,
    "roof_bump":      0.30,
    "roof_tile":      _hex("#2E2E30"),
    "roof_metal":     _hex("#2A2A2C"),
    "accent":         _hex("#9E4C26"),  # Burnt terracotta (hygge accent)
    "frame":          _hex("#1A1A1E"),  # Dark charcoal — strong contrast with white wall
    "frame_metal":    0.40,
    "column":         _hex("#5C4433"),  # Dark wenge — distinct from white wall
    "wood_dark":      _hex("#5C4433"),  # Dark wenge
    "wood_light":     _hex("#C8A878"),  # Light oak floorboards
    "glass":          _hex("#D2E8F0"),  # Cool Scandinavian light
    "glass_alpha":    0.10,
    "glass_rough":    0.02,
    "ground":         _hex("#3D362A"),
    "grass":          _hex("#285220"),
    "pavement":       _hex("#A09C96"),
    "gravel":         _hex("#9C9890"),
    "sand":           _hex("#B8B2A8"),
    "path":           _hex("#A89E94"),
    "pool_water":     _hex("#3D9CB8"),  # Cool fjord-blue
    "pool_water_alpha": 0.55,
    "pool_water_trans": 0.85,
    "pool_tile":      _hex("#D2E8F0"),
    "water":          _hex("#3D9CB8"),
    "water_alpha":    0.55,
    "water_trans":    0.85,
    "foliage_a":      _hex("#285220"),
    "foliage_b":      _hex("#1E3D18"),
    "foliage_dark":   _hex("#142810"),
    "bark":           _hex("#4D3A28"),
    "interior_floor": _hex("#C8A878"),  # Light oak
    "interior_wall":  _hex("#F2F0ED"),  # Pure white
    "interior_ceil":  _hex("#F5F3F0"),
    "sofa":           _hex("#8A7A6E"),  # Grey linen
    "cushion_accent": _hex("#9E4C26"),  # Burnt terracotta cushions
    "table_top":      _hex("#C8A878"),  # Light oak
    "lantern":        True,
    "lantern_color":  _hex("#FFCF80"),  # Candle glow (hygge warmth)
    "sky_turbidity":  1.8,
    "sun_energy":     4.0,
    "sun_color":      _hex("#FFE8C0"),  # Soft Nordic afternoon
    "fill_energy":    300,
    "fill_color":     _hex("#F0F4FF"),  # Cool overcast fill
    "shadow_color":   _hex("#6070A8"),
    "sun_elevation":  28.0,
    "sun_rotation":   220.0,
    "ambient_strength": 1.2,
    "fog":            True,
    "fog_color":      _hex("#C8D8E8"),
    "fog_density":    0.05,
}

# ─────────────────────────────────────────────────────────────────────────────
# INDUSTRIAL  — Raw concrete, exposed red brick, steel, dark dramatic lighting
# ─────────────────────────────────────────────────────────────────────────────
_INDUSTRIAL: Pal = {
    "wall":           _hex("#858075"),  # Raw concrete
    "wall_rough":     0.95,
    "wall_bump":      0.65,
    "wall_wood":      _hex("#3D3028"),  # Charred timber
    "wall_brick":     _hex("#9E4730"),  # Exposed red brick
    "facade":         _hex("#858075"),
    "slab":           _hex("#8A8680"),
    "concrete":       _hex("#8C8880"),
    "roof":           _hex("#474748"),  # Dark corrugated
    "roof_rough":     0.30,
    "roof_bump":      0.25,
    "roof_tile":      _hex("#474748"),
    "roof_metal":     _hex("#565658"),
    "accent":         _hex("#B85218"),  # Corten rust accent
    "frame":          _hex("#2E2E30"),  # Black steel
    "frame_metal":    0.95,
    "column":         _hex("#8A8680"),
    "wood_dark":      _hex("#3D3028"),
    "wood_light":     _hex("#7A6850"),  # Reclaimed timber
    "glass":          _hex("#98B8C8"),  # Factory glass — cool grey-blue
    "glass_alpha":    0.08,
    "glass_rough":    0.04,
    "steel":          _hex("#A5A5A8"),
    "ground":         _hex("#2E2A22"),  # Dark asphalt ground
    "grass":          _hex("#233018"),  # Sparse industrial scrub
    "pavement":       _hex("#4A4844"),  # Cracked concrete yard
    "gravel":         _hex("#5A5650"),
    "asphalt":        _hex("#1E1E20"),
    "sand":           _hex("#8A8070"),
    "path":           _hex("#5A5650"),
    "pool_water":     _hex("#304858"),  # Moody dark pool
    "pool_water_alpha": 0.65,
    "pool_water_trans": 0.80,
    "pool_tile":      _hex("#5A6870"),
    "water":          _hex("#304858"),
    "water_alpha":    0.65,
    "water_trans":    0.80,
    "foliage_a":      _hex("#233018"),
    "foliage_b":      _hex("#1A2610"),
    "foliage_dark":   _hex("#121C08"),
    "bark":           _hex("#3A2C1E"),
    "corten":         _hex("#853D26"),
    "corrugated":     _hex("#7A7A80"),
    "exposed_conc":   _hex("#8C8A85"),
    "interior_floor": _hex("#5A5650"),  # Polished concrete floor
    "interior_wall":  _hex("#858075"),  # Raw concrete walls
    "interior_ceil":  _hex("#4A4848"),  # Dark steel ceiling
    "sofa":           _hex("#3A3530"),  # Dark leather
    "cushion_accent": _hex("#B85218"),  # Rust-orange accent
    "table_top":      _hex("#7A6850"),  # Reclaimed timber table
    "lantern":        True,
    "lantern_color":  _hex("#FF8820"),  # Industrial Edison bulb
    "sky_turbidity":  4.0,
    "sun_energy":     3.5,
    "sun_color":      _hex("#FFB860"),  # Overcast diffused
    "fill_energy":    220,
    "fill_color":     _hex("#708090"),  # Cool grey fill
    "shadow_color":   _hex("#1A1C28"),  # Near-black deep shadows
    "sun_elevation":  35.0,
    "sun_rotation":   190.0,
    "ambient_strength": 0.9,
    "fog":            True,
    "fog_color":      _hex("#606870"),
    "fog_density":    0.12,
}

# ─────────────────────────────────────────────────────────────────────────────
# COLONIAL / CRAFTSMAN  — White trim, clapboard siding, warm brick & deep blues
# ─────────────────────────────────────────────────────────────────────────────
_COLONIAL: Pal = {
    "wall":           _hex("#F2F0EC"),  # White clapboard siding
    "wall_rough":     0.85,
    "wall_bump":      0.20,
    "wall_wood":      _hex("#C8B898"),  # Light timber trim
    "wall_brick":     _hex("#9E6050"),  # Colonial brick
    "facade":         _hex("#F2F0EC"),
    "slab":           _hex("#C8C4BC"),
    "concrete":       _hex("#CCCAC4"),
    "roof":           _hex("#383638"),  # Dark slate grey
    "roof_rough":     0.88,
    "roof_bump":      0.35,
    "roof_tile":      _hex("#383638"),
    "roof_metal":     _hex("#383638"),
    "accent":         _hex("#1E2E60"),  # Deep navy blue trim
    "frame":          _hex("#142018"),  # Dark hunter green — classic colonial
    "frame_metal":    0.0,
    "column":         _hex("#F2F0EC"),  # White columns
    "wood_dark":      _hex("#4A3826"),
    "wood_light":     _hex("#C8A870"),  # Warm oak
    "glass":          _hex("#CCE8D0"),  # Soft green-tinted panes
    "glass_alpha":    0.15,
    "glass_rough":    0.03,
    "ground":         _hex("#3D3626"),
    "grass":          _hex("#305A1E"),
    "pavement":       _hex("#B8B4A8"),  # Light concrete path
    "gravel":         _hex("#A8A49E"),
    "sand":           _hex("#C8BEA8"),
    "path":           _hex("#B0AC9E"),
    "pool_water":     _hex("#1E90C0"),  # Classic backyard pool
    "pool_water_alpha": 0.60,
    "pool_water_trans": 0.88,
    "pool_tile":      _hex("#90CBDF"),
    "water":          _hex("#1E90C0"),
    "water_alpha":    0.60,
    "water_trans":    0.88,
    "foliage_a":      _hex("#305A1E"),
    "foliage_b":      _hex("#264A18"),
    "foliage_dark":   _hex("#1A3010"),
    "bark":           _hex("#4D3320"),
    "white_paint":    _hex("#F5F3F0"),
    "interior_floor": _hex("#C8A870"),  # Warm hardwood floors
    "interior_wall":  _hex("#F0EDE8"),  # Off-white plaster
    "interior_ceil":  _hex("#F5F3F0"),  # White
    "sofa":           _hex("#7A6A58"),  # Warm taupe linen
    "cushion_accent": _hex("#1E2E60"),  # Navy accent cushions
    "table_top":      _hex("#C8A870"),  # Warm oak dining table
    "lantern":        True,
    "lantern_color":  _hex("#FFD080"),  # Warm incandescent
    "sky_turbidity":  2.2,
    "sun_energy":     5.0,
    "sun_color":      _hex("#FFF0D0"),  # Warm afternoon
    "fill_energy":    310,
    "fill_color":     _hex("#FFF5E5"),
    "shadow_color":   _hex("#485870"),
    "sun_elevation":  42.0,
    "sun_rotation":   210.0,
    "ambient_strength": 1.3,
    "fog":            False,
}

# ─────────────────────────────────────────────────────────────────────────────
# CLASSICAL / GREEK-ROMAN  — Marble white, warm stone, formal symmetry
# ─────────────────────────────────────────────────────────────────────────────
_CLASSICAL: Pal = {
    "wall":           _hex("#EEE9DC"),  # Warm Carrara marble plaster
    "wall_rough":     0.80,
    "wall_bump":      0.30,
    "wall_wood":      _hex("#8C7050"),  # Aged timber
    "wall_brick":     _hex("#C0A882"),  # Warm sandstone
    "facade":         _hex("#EEE9DC"),
    "slab":           _hex("#D8D2C0"),  # Stone slab
    "concrete":       _hex("#D0CAB8"),
    "roof":           _hex("#8C5A3C"),  # Warm terracotta-clay
    "roof_rough":     0.78,
    "roof_bump":      0.45,
    "roof_tile":      _hex("#8C5A3C"),
    "roof_metal":     _hex("#7A6040"),
    "accent":         _hex("#A87A30"),  # Greek gold leaf
    "frame":          _hex("#3A3028"),  # Dark bronze — contrasts with stone wall
    "frame_metal":    0.30,
    "column":         _hex("#B8A88A"),  # Warm travertine — darker than wall
    "wood_dark":      _hex("#5C3C20"),
    "wood_light":     _hex("#A88050"),
    "glass":          _hex("#A8CCAC"),  # Aged green glass
    "glass_alpha":    0.20,
    "glass_rough":    0.04,
    "ground":         _hex("#4A4030"),
    "grass":          _hex("#385A22"),
    "pavement":       _hex("#C8BEA0"),  # Limestone courtyard
    "gravel":         _hex("#C0B898"),
    "sand":           _hex("#C8BEA0"),
    "path":           _hex("#B8AE90"),
    "pool_water":     _hex("#1478A0"),  # Deep classical pool
    "pool_water_alpha": 0.65,
    "pool_water_trans": 0.88,
    "pool_tile":      _hex("#A0C8D8"),
    "water":          _hex("#1478A0"),
    "water_alpha":    0.65,
    "water_trans":    0.88,
    "foliage_a":      _hex("#385A22"),
    "foliage_b":      _hex("#2C481A"),
    "foliage_dark":   _hex("#1A2E0E"),
    "bark":           _hex("#4D3320"),
    "marble":         _hex("#EEECE8"),
    "white_paint":    _hex("#EEEAE0"),
    "terracotta":     _hex("#A05C38"),
    "interior_floor": _hex("#C0AE80"),  # Warm stone tile
    "interior_wall":  _hex("#EEE9DC"),  # Marble plaster
    "interior_ceil":  _hex("#EEEAE0"),  # Painted white
    "sofa":           _hex("#7A6848"),  # Gold-beige draped fabric
    "cushion_accent": _hex("#A87A30"),  # Gold accent
    "table_top":      _hex("#C0AE80"),  # Stone table
    "lantern":        True,
    "lantern_color":  _hex("#FFCF60"),  # Torch/oil lamp warmth
    "sky_turbidity":  2.0,
    "sun_energy":     5.5,
    "sun_color":      _hex("#FFE8B8"),  # Mediterranean noon
    "fill_energy":    340,
    "fill_color":     _hex("#FFF8E8"),
    "shadow_color":   _hex("#504060"),
    "sun_elevation":  55.0,
    "sun_rotation":   195.0,
    "ambient_strength": 1.4,
    "fog":            False,
}

# ─────────────────────────────────────────────────────────────────────────────
# MODERN  — Cool greys, floor-to-ceiling glass, matte black steel
# ─────────────────────────────────────────────────────────────────────────────
_MODERN: Pal = {
    "wall":           _hex("#D2CDCA"),
    "wall_rough":     0.85,
    "wall_bump":      0.50,
    "wall_wood":      _hex("#7A6050"),
    "wall_brick":     _hex("#988880"),
    "facade":         _hex("#D2CDCA"),
    "slab":           _hex("#B8B4AE"),
    "concrete":       _hex("#9E9A94"),
    "roof":           _hex("#262628"),  # Flat dark roof
    "roof_rough":     0.70,
    "roof_bump":      0.30,
    "roof_tile":      _hex("#262628"),
    "roof_metal":     _hex("#303032"),
    "accent":         _hex("#406CA5"),
    "frame":          _hex("#141416"),  # Matte black aluminium
    "frame_metal":    0.90,
    "column":         _hex("#6A5C4A"),  # Dark warm grey — contrasts with wall
    "wood_dark":      _hex("#472D20"),
    "wood_light":     _hex("#9E7245"),
    "glass":          _hex("#B8E0F7"),  # Floor-to-ceiling glazing
    "glass_alpha":    0.12,
    "glass_rough":    0.02,
    "ground":         _hex("#332E24"),
    "grass":          _hex("#2E7326"),
    "pavement":       _hex("#99958A"),
    "gravel":         _hex("#7A7670"),
    "asphalt":        _hex("#1F1F21"),
    "sand":           _hex("#C6B88C"),
    "path":           _hex("#A69F96"),
    "pool_water":     _hex("#0A85C8"),
    "pool_water_alpha": 0.65,
    "pool_water_trans": 0.85,
    "pool_tile":      _hex("#C8E6F2"),
    "water":          _hex("#0D6699"),
    "water_alpha":    0.55,
    "water_trans":    0.88,
    "foliage_a":      _hex("#2E7326"),
    "foliage_b":      _hex("#245C1E"),
    "foliage_dark":   _hex("#0F471A"),
    "bark":           _hex("#4D3320"),
    "interior_floor": _hex("#9E7245"),  # Light oak
    "interior_wall":  _hex("#E8DDD0"),
    "interior_ceil":  _hex("#F2F0ED"),
    "sofa":           _hex("#8A8280"),  # Concrete grey
    "cushion_accent": _hex("#406CA5"),  # Blue accent
    "table_top":      _hex("#9E7245"),
    "lantern":        True,
    "lantern_color":  _hex("#FFCF80"),
    "sky_turbidity":  2.5,
    "sun_energy":     5.5,
    "sun_color":      _hex("#FFFFF0"),  # Cool midday
    "fill_energy":    320,
    "fill_color":     _hex("#E8F2FF"),  # Slight blue fill
    "shadow_color":   _hex("#405070"),
    "sun_elevation":  42.0,
    "sun_rotation":   215.0,
    "ambient_strength": 1.3,
    "fog":            False,
}

# ─────────────────────────────────────────────────────────────────────────────
# ASIAN (Chinese/Pan-Asian)  — Crimson lacquer, jade green, gold leaf
# ─────────────────────────────────────────────────────────────────────────────
_ASIAN: Pal = {
    "wall":           _hex("#E0D8C8"),
    "wall_rough":     0.80,
    "wall_bump":      0.40,
    "wall_wood":      _hex("#5C2820"),  # Lacquer red timber
    "wall_brick":     _hex("#9E6040"),
    "facade":         _hex("#E0D8C8"),
    "slab":           _hex("#9A9288"),
    "concrete":       _hex("#9A9288"),
    "roof":           _hex("#942018"),  # Vermillion roof
    "roof_rough":     0.60,
    "roof_bump":      0.50,
    "roof_tile":      _hex("#942018"),
    "roof_metal":     _hex("#C8A020"),  # Gold leaf ridge
    "accent":         _hex("#C8A020"),  # Gold leaf
    "frame":          _hex("#8C1410"),  # Lacquer red
    "frame_metal":    0.10,
    "column":         _hex("#E0D8C8"),
    "wood_dark":      _hex("#5C2820"),
    "wood_light":     _hex("#A86830"),
    "glass":          _hex("#B8D8C0"),  # Jade-tinted glazing
    "glass_alpha":    0.20,
    "glass_rough":    0.03,
    "ground":         _hex("#38301A"),
    "grass":          _hex("#206018"),
    "pavement":       _hex("#C0B088"),
    "gravel":         _hex("#9C9488"),
    "sand":           _hex("#C0B088"),
    "path":           _hex("#B0A880"),
    "pool_water":     _hex("#0E7858"),  # Deep jade green
    "pool_water_alpha": 0.55,
    "pool_water_trans": 0.85,
    "pool_tile":      _hex("#607A70"),
    "water":          _hex("#0E7858"),
    "water_alpha":    0.55,
    "water_trans":    0.85,
    "foliage_a":      _hex("#206018"),
    "foliage_b":      _hex("#184E14"),
    "foliage_dark":   _hex("#0E3810"),
    "bark":           _hex("#4D3320"),
    "bamboo":         _hex("#8FAF44"),
    "stone_zen":      _hex("#9C9488"),
    "interior_floor": _hex("#C09040"),  # Warm lacquered wood
    "interior_wall":  _hex("#E0D8C8"),  # Pale celadon
    "interior_ceil":  _hex("#5C2820"),  # Lacquer red beams
    "sofa":           _hex("#C8A020"),  # Gold brocade
    "cushion_accent": _hex("#942018"),  # Vermillion cushions
    "table_top":      _hex("#A86830"),  # Rosewood
    "lantern":        True,
    "lantern_color":  _hex("#FF9820"),  # Red paper lantern glow
    "sky_turbidity":  2.0,
    "sun_energy":     5.0,
    "sun_color":      _hex("#FFE0B0"),
    "fill_energy":    300,
    "fill_color":     _hex("#FFF0E0"),
    "shadow_color":   _hex("#503840"),
    "sun_elevation":  40.0,
    "sun_rotation":   205.0,
    "ambient_strength": 1.3,
    "fog":            True,
    "fog_color":      _hex("#D8C8B0"),
    "fog_density":    0.06,
}


# ─────────────────────────────────────────────────────────────────────────────
# CLEAN — Light blue, airy, minimal, very clean
# ─────────────────────────────────────────────────────────────────────────────
_CLEAN: Pal = {
    "wall":           _hex("#E8F4F8"),  # Light ice blue
    "wall_rough":     0.75,
    "wall_bump":      0.20,
    "wall_wood":      _hex("#B8D8E8"),  # Pale blue-grey
    "wall_brick":     _hex("#D0E8F0"),  # Faded blue
    "facade":         _hex("#E8F4F8"),
    "slab":           _hex("#D8EAF0"),  # Pale blue-grey
    "concrete":       _hex("#C8DCE8"),
    "roof":           _hex("#B0D0E0"),  # Soft powder blue
    "roof_rough":     0.60,
    "roof_bump":      0.20,
    "roof_tile":      _hex("#B0D0E0"),
    "roof_metal":     _hex("#A0C0D0"),
    "accent":         _hex("#206080"),  # Deep ocean blue — visible against light wall
    "frame":          _hex("#1A2A3A"),  # Dark navy — strong contrast
    "frame_metal":    0.15,
    "column":         _hex("#4A6A7A"),  # Steel grey-blue — distinct from wall
    "wood_dark":      _hex("#B8C8D0"),
    "wood_light":     _hex("#D8E8F0"),
    "glass":          _hex("#C8E8F8"),  # Clear light blue glass
    "glass_alpha":    0.12,
    "glass_rough":    0.01,
    "ground":         _hex("#E0E4E0"),  # Light grey ground
    "grass":          _hex("#C8E0C8"),  # Pale muted green
    "pavement":       _hex("#E0E4E8"),  # Light stone
    "gravel":         _hex("#D8DCD8"),
    "sand":           _hex("#E8E8E0"),
    "path":           _hex("#D0D8D8"),
    "pool_water":     _hex("#80C8E8"),  # Clean pool blue
    "pool_water_alpha": 0.50,
    "pool_water_trans": 0.85,
    "pool_tile":      _hex("#A0D8F0"),
    "water":          _hex("#80C8E8"),
    "water_alpha":    0.50,
    "water_trans":    0.85,
    "foliage_a":      _hex("#B0D8B0"),  # Pale fresh green
    "foliage_b":      _hex("#98C8A0"),
    "foliage_dark":   _hex("#80B888"),
    "bark":           _hex("#C0C8C0"),
    "terracotta":     _hex("#D0DCE0"),
    "plaster":        _hex("#E8F4F8"),
    "marble":         _hex("#F0F4F8"),
    "interior_floor": _hex("#D8EAF0"),
    "interior_wall":  _hex("#E8F4F8"),
    "interior_ceil":  _hex("#F0F8FC"),
    "sofa":           _hex("#C8DCE8"),
    "cushion_accent": _hex("#B0D8F0"),  # Light blue accent
    "table_top":      _hex("#D8E8F0"),
    "lantern":        False,
    "sky_turbidity":  1.8,
    "sun_energy":     4.5,
    "sun_color":      _hex("#FFF5E8"),  # Soft warm light
    "fill_energy":    280,
    "fill_color":     _hex("#F0F8FC"),
    "shadow_color":   _hex("#8098A8"),
    "sun_elevation":  45.0,
    "sun_rotation":   210.0,
    "ambient_strength": 1.2,
    "fog":            True,
    "fog_color":      _hex("#E0ECF0"),
    "fog_density":    0.03,
}


# ─────────────────────────────────────────────────────────────────────────────
# Master registry
# ─────────────────────────────────────────────────────────────────────────────
STYLE_PALETTES: dict[str, Pal] = {
    "japanese":     _JAPANESE,
    "villa":        _VILLA,
    "italian":      _VILLA,        # alias
    "mediterranean":_VILLA,        # alias
    "scandinavian": _SCANDINAVIAN,
    "nordic":       _SCANDINAVIAN, # alias
    "industrial":   _INDUSTRIAL,
    "colonial":     _COLONIAL,
    "craftsman":    _COLONIAL,     # alias
    "classical":    _CLASSICAL,
    "greek":        _CLASSICAL,    # alias
    "modern":       _MODERN,
    "contemporary": _MODERN,       # alias
    "asian":        _ASIAN,
    "chinese":      _ASIAN,        # alias
    "clean":        _CLEAN,
}


def get_palette(style_name: str) -> Pal:
    """Return the merged material palette for *style_name*.

    Any slot not found in the style-specific palette is transparently
    filled from the ``_BASE`` fallback, so callers can always look up any
    slot without guarding for ``KeyError``.
    """
    base = style_name.lower().strip()
    style_pal = STYLE_PALETTES.get(base, _MODERN)
    # Merge: style overrides take priority over _BASE defaults
    merged = {**_BASE, **style_pal}
    return merged


def get_lighting_config(style_name: str) -> dict[str, Any]:
    """Return the lighting-specific subset of the palette for *style_name*."""
    pal = get_palette(style_name)
    LIGHTING_KEYS = {
        "sky_turbidity", "sun_energy", "sun_color", "fill_energy",
        "fill_color", "shadow_color", "sun_elevation", "sun_rotation",
        "ambient_strength", "fog", "fog_color", "fog_density",
    }
    return {k: pal[k] for k in LIGHTING_KEYS if k in pal}


def list_styles() -> list[str]:
    """Return sorted list of all registered style names (including aliases)."""
    return sorted(STYLE_PALETTES.keys())
