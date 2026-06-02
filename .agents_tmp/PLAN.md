# AI Architect - Dynamic BOQ & Cost Estimation Feature

## 1. OBJECTIVE

Add a comprehensive **Bill of Quantities (BOQ) component** with dynamic building measurements that auto-calculates all construction details based on plot size. When a user enters a plot size (e.g., 500 sqm), the system should calculate:
- Number of floors based on FAR
- Ceiling height, building width, depth, total height
- Window dimensions and count
- Interior vs exterior measurements
- Accurate material quantities
- Cost per square feet in INR/USD

## 2. CONTEXT SUMMARY

| Component | Status |
|-----------|--------|
| BOQ Modal UI | ✅ Exists in `page.tsx` (lines 235-299) - displays static data |
| Store (`boqData`) | ✅ Exists with `setBoqData()` action |
| Trigger Button | ❌ Missing - no way to open BOQ modal |
| Calculation Logic | ❌ None - no cost/material calculations |

### Target Files
- `frontend/src/app/page.tsx` - Add Cost tab to sidebar
- `frontend/src/lib/store.ts` - Add BOQ state management
- `frontend/src/lib/boqCalculator.ts` (NEW) - Calculation engine
- `frontend/src/components/BOQPanel.tsx` (NEW) - Full BOQ UI

## 3. APPROACH OVERVIEW

Create a new **BOQ Panel** tab in the left sidebar that provides:

1. **Auto-calculation Engine** - Takes plot size → returns complete building specs
2. **Dynamic Updates** - All values change when plot size changes
3. **Floor-by-Floor Breakdown** - Detailed measurements per floor
4. **Material Quantities** - Accurate volumes/weights
5. **Cost Estimation** - INR with USD conversion

The calculation follows **NBC 2016** standards for Indian construction.

## 4. IMPLEMENTATION STEPS

### Step 1: Create BOQ Calculator Utility
**Goal:** Build calculation engine for all building measurements

**Method:** Create `frontend/src/lib/boqCalculator.ts` with:
- `calculateBuildingConfig(plotAreaSqM)` → { floors, coverage, width, depth, setbacks }
- `calculateHeights(floors, ceilingHeight)` → { ceilingHeight, slabThickness, totalHeight }
- `calculateDimensions(buildingWidth, buildingDepth, wallThickness)` → { exteriorWidth, exteriorDepth, interiorWidth, interiorDepth }
- `calculateWindows(floorArea, ceilingHeight)` → { count, width, height, glassArea }
- `calculateMaterialQuantities(config)` → { concrete_m3, steel_kg, bricks_nos, glass_m2, wood_m3 }
- `calculateCosts(area, quality)` → { costPerSqft, totalINR, totalUSD, breakdown }

**Reference:** New file `frontend/src/lib/boqCalculator.ts`

---

### Step 2: Add BOQ Types to Store
**Goal:** Add interfaces and state for BOQ calculations

**Method:** Update `frontend/src/lib/store.ts`:
- Add `BOQSpec` interface with all building parameters
- Add `boqSpec: BOQSpec | null` to store state
- Add `setBoqSpec()` and `calculateBOQ()` actions

**Reference:** `frontend/src/lib/store.ts`

---

### Step 3: Create BOQPanel Component
**Goal:** Build complete BOQ UI with all dynamic calculations

**Method:** Create `frontend/src/components/BOQPanel.tsx` with sections:

#### Section A: Plot Input
- Plot size (auto from PlotFeasibility or manual)
- Building type dropdown (apartment, villa, rowhouse)
- Quality tier (basic, standard, premium)

#### Section B: Building Specifications (Auto-Calculated)
| Parameter | Formula |
|-----------|---------|
| Floors | Based on plot size + FAR |
| Coverage | 35-60% based on plot size |
| Building Width | plot_width - setbacks |
| Building Depth | plot_depth - setbacks |
| Ceiling Height | 3.0m (standard), 3.2m (premium) |
| Total Height | floors × (ceiling + slab) |
| Wall Thickness | 0.3m (exterior), 0.15m (interior) |

#### Section C: Dimensions Breakdown
```
EXTERIOR DIMENSIONS:
- Width: __ m
- Depth: __ m  
- Height: __ m

INTERIOR DIMENSIONS:
- Net Width: __ m (exterior - 2×wall)
- Net Depth: __ m (exterior - 2×wall)
- Per Floor Area: __ m²
- Total Area: __ m² (__ sqft)

SETBACKS:
- Front: 1.5m
- Back: 1.0m
- Sides: 0.5m each
```

#### Section D: Windows & Doors
```
WINDOWS:
- Height: ceiling × 0.5
- Width: 1.2m (standard), 1.5m (large)
- Count per floor: (width / 3) × 2 sides

DOORS:
- Main door: 2.1m × 0.9m
- Room doors: 2.0m × 0.8m
- Bathroom: 2.0m × 0.7m
```

#### Section E: Material Quantities
```
STRUCTURAL:
- Concrete (m³): Footprint × (foundation + slabs)
- Steel (kg): Concrete × 100 kg/m³
- Bricks (nos): Wall area × 500/m²

FINISHING:
- Cement bags: Wall area × 0.4
- Sand (m³): Wall area × 0.02
- Glass (m²): Window count × 1.8
- Wood (m³): Doors × 0.05
```

#### Section F: Cost Estimation
```
RATE_PER_SQFT:
- Basic: ₹1,800/sqft
- Standard: ₹2,200/sqft  
- Premium: ₹2,800/sqft

BREAKDOWN:
- Structure (40%): ₹__
- Walls & Finishes (25%): ₹__
- Doors & Windows (10%): ₹__
- Electrical (8%): ₹__
- Plumbing (7%): ₹__
- Flooring (5%): ₹__
- Misc (5%): ₹__

TOTAL INR: ₹__
TOTAL USD: $__
COST/SQFT: ₹__/sqft
```

**Reference:** New file `frontend/src/components/BOQPanel.tsx`

---

### Step 4: Add Cost Tab to Left Sidebar
**Goal:** Integrate BOQ panel into the sidebar

**Method:** Update `frontend/src/app/page.tsx`:
1. Add `"cost"` to `leftTab` type: `"chat"|"ai"|"plot"|"cost"|"style"`
2. Add tab button for "Cost" with calculator icon
3. Show `<BOQPanel />` when `leftTab === "cost"`
4. Add "Estimate Cost" button in toolbar (after Generate)

**Reference:** `frontend/src/app/page.tsx`

---

### Step 5: Connect with PlotFeasibility
**Goal:** Auto-populate BOQ when user changes plot size

**Method:**
- Sync `plotWidth`, `plotDepth` to BOQPanel
- When PlotFeasibility calculates, update BOQ auto-matically
- Recalculate all values on plot size change

**Reference:** `PlotFeasibility.tsx`, `BOQPanel.tsx`

## 5. DYNAMIC CALCULATION RULES

### Plot Size → Floor Count
| Plot Size | Floors | Coverage |
|-----------|--------|----------|
| 100-200 sqm | 1 | 60% |
| 200-400 sqm | 2 | 55% |
| 400-600 sqm | 2-3 | 50% |
| 600-900 sqm | 3-4 | 45% |
| 900-1200 sqm | 4-5 | 40% |
| 1200+ sqm | 5+ | 35% |

### Dimensions Calculation Example (500 sqm)
```
PLOT: 500 sqm (20m × 25m)

SETBACKS:
- Front: 1.5m
- Back: 1.0m  
- Left: 0.5m
- Right: 0.5m

BUILDABLE AREA:
- Width: 20 - 2 = 18m
- Depth: 25 - 2.5 = 22.5m

COVERAGE (50% for 500sqm):
- Max footprint: 250 sqm

BUILDING:
- Width: 15m
- Depth: 16m
- Footprint: 240 sqm ✓

FLOORS (FAR 3.5):
- Max area: 500 × 3.5 = 1750 sqm
- Floors: 1750 / 240 = 7.2 → 3 floors

FINAL:
- 3 floors × 240 sqm = 720 sqm
- FAR achieved: 720/500 = 1.44 (within 3.5)
```

### Cost Calculation
```
BASE_RATE = ₹2,200/sqft (standard)

TOTAL_AREA_SQFT = total_area_m2 × 10.764

STRUCTURE_COST = total × 40%
WALLS_COST = total × 25%
DOORS_COST = total × 10%
ELECTRICAL_COST = total × 8%
PLUMBING_COST = total × 7%
FLOORING_COST = total × 5%
MISC_COST = total × 5%

TOTAL_INR = sum of all
TOTAL_USD = TOTAL_INR / 83
```

## 6. TESTING AND VALIDATION

### Test Case 1: Small Plot (200 sqm)
- Input: 200 sqm plot
- Expected: 1-2 floors, ~10m × 10m, Cost: ~₹48L

### Test Case 2: Medium Plot (500 sqm)
- Input: 500 sqm plot
- Expected: 2-3 floors, ~15m × 16m, Ceiling: 3.0m, Cost: ~₹1.8Cr

### Test Case 3: Large Plot (1000 sqm)
- Input: 1000 sqm plot
- Expected: 4-5 floors, ~20m × 22m, Ceiling: 3.2m, Cost: ~₹5Cr

### Success Criteria:
- [ ] Cost tab appears in left sidebar with calculator icon
- [ ] Plot size auto-populates from PlotFeasibility
- [ ] Floors update when plot size changes
- [ ] All dimensions (width, depth, height) update dynamically
- [ ] Window count/dimensions calculated correctly
- [ ] Material quantities are accurate
- [ ] Cost shows in INR with USD conversion
- [ ] BOQ updates in real-time as plot size changes
