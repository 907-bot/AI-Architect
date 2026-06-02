"use client";
import React, { useState, useEffect, useCallback } from "react";
import { useStore } from "@/lib/store";
import {
  Calculator, Ruler, Home, Layers, DoorOpen, Window, Hammer,
  Zap, Droplets, Square, Paintbrush, ChevronDown, ChevronRight,
  IndianRupee, DollarSign, Building2, Package
} from "lucide-react";

type Quality = "basic" | "standard" | "premium";
type BuildingType = "apartment" | "villa" | "rowhouse";

interface SectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function Section({ title, icon, children, defaultOpen = true }: SectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-700 rounded-lg overflow-hidden bg-gray-800/50">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-4 py-3 bg-gray-800 hover:bg-gray-750 transition-colors text-left"
      >
        {icon}
        <span className="font-medium text-gray-200">{title}</span>
        {isOpen ? <ChevronDown className="ml-auto w-4 h-4" /> : <ChevronRight className="ml-auto w-4 h-4" />}
      </button>
      {isOpen && <div className="p-4 space-y-2">{children}</div>}
    </div>
  );
}

interface DataRowProps {
  label: string;
  value: string | number;
  unit?: string;
  highlight?: boolean;
}

function DataRow({ label, value, unit, highlight }: DataRowProps) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className={`text-sm font-mono ${highlight ? "text-emerald-400 font-semibold" : "text-gray-200"}`}>
        {value}{unit && <span className="text-gray-500 ml-1">{unit}</span>}
      </span>
    </div>
  );
}

// Safe format functions with fallbacks
function formatINRSafe(amount: number): string {
  if (typeof amount !== 'number' || isNaN(amount)) return '₹0';
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)} Cr`;
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)} L`;
  return `₹${amount.toLocaleString('en-IN')}`;
}

function formatUSDSafe(amount: number): string {
  if (typeof amount !== 'number' || isNaN(amount)) return '$0';
  return `$${amount.toLocaleString('en-US')}`;
}

function NumberDisplay({ value, decimals = 0 }: { value: number; decimals?: number }) {
  if (typeof value !== 'number' || isNaN(value)) return <span>0</span>;
  return <span>{value.toFixed(decimals)}</span>;
}

export default function BOQPanel() {
  // Use individual selectors to avoid selector function recreations
  const plotWidth = useStore((s) => s.plotWidth ?? 20);
  const plotDepth = useStore((s) => s.plotDepth ?? 25);
  const boqSpec = useStore((s) => s.boqSpec);
  const calculateBoq = useStore((s) => s.calculateBoq);
  
  const [plotArea, setPlotArea] = useState<number>(500);
  const [quality, setQuality] = useState<Quality>("standard");
  const [buildingType, setBuildingType] = useState<BuildingType>("apartment");
  const [initialized, setInitialized] = useState(false);
  const [localBoqSpec, setLocalBoqSpec] = useState<any>(null);

  // Initialize on mount - compute local boqSpec to avoid store access issues
  useEffect(() => {
    setInitialized(true);
    // Compute initial BOQ
    const area = (plotWidth || 20) * (plotDepth || 25);
    setPlotArea(area);
    
    // Import and call calculateBOQ directly
    import("@/lib/boqCalculator").then(({ calculateBOQ, getCeilingHeight }) => {
      const ceiling = getCeilingHeight(quality);
      const spec = calculateBOQ(area, quality, ceiling);
      setLocalBoqSpec(spec);
      if (calculateBoq) {
        calculateBoq(area, quality);
      }
    });
  }, []);

  // Recalculate when user changes inputs
  const handleRecalculate = React.useCallback(() => {
    import("@/lib/boqCalculator").then(({ calculateBOQ, getCeilingHeight }) => {
      const ceiling = getCeilingHeight(quality);
      const spec = calculateBOQ(plotArea, quality, ceiling);
      setLocalBoqSpec(spec);
      if (calculateBoq) {
        calculateBoq(plotArea, quality);
      }
    });
  }, [plotArea, quality, calculateBoq]);

  // Handle quality change
  const handleQualityChange = React.useCallback((newQuality: Quality) => {
    setQuality(newQuality);
    import("@/lib/boqCalculator").then(({ calculateBOQ, getCeilingHeight }) => {
      const ceiling = getCeilingHeight(newQuality);
      const spec = calculateBOQ(plotArea, newQuality, ceiling);
      setLocalBoqSpec(spec);
      if (calculateBoq) {
        calculateBoq(plotArea, newQuality);
      }
    });
  }, [plotArea, calculateBoq]);

  // Handle plot area change
  const handlePlotAreaChange = React.useCallback((newArea: number) => {
    setPlotArea(newArea);
    import("@/lib/boqCalculator").then(({ calculateBOQ, getCeilingHeight }) => {
      const ceiling = getCeilingHeight(quality);
      const spec = calculateBOQ(newArea, quality, ceiling);
      setLocalBoqSpec(spec);
      if (calculateBoq) {
        calculateBoq(newArea, quality);
      }
    });
  }, [quality, calculateBoq]);

  if (!initialized) {
    return (
      <div className="h-full flex flex-col bg-gray-900 text-gray-100">
        <div className="flex-shrink-0 px-4 py-3 bg-gray-800 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-emerald-400" />
            <h2 className="font-semibold text-gray-100">Bill of Quantities</h2>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-gray-400">Loading...</div>
        </div>
      </div>
    );
  }

  // Use localBoqSpec if available, otherwise create from store
  const activeBoqSpec = localBoqSpec || boqSpec;

  if (!activeBoqSpec) {
    return (
      <div className="h-full flex flex-col bg-gray-900 text-gray-100">
        <div className="flex-shrink-0 px-4 py-3 bg-gray-800 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Calculator className="w-5 h-5 text-emerald-400" />
            <h2 className="font-semibold text-gray-100">Bill of Quantities</h2>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-400">
            <Calculator className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>No BOQ data available</p>
            <button
              onClick={handleRecalculate}
              className="mt-3 px-4 py-2 bg-emerald-600 text-white rounded text-sm"
            >
              Generate BOQ
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Extract values safely
  const config = activeBoqSpec.config || {};
  const heights = activeBoqSpec.heights || {};
  const dimensions = activeBoqSpec.dimensions || {};
  const setbacks = activeBoqSpec.setbacks || {};
  const windows = activeBoqSpec.windows || {};
  const doors = activeBoqSpec.doors || {};
  const materials = activeBoqSpec.materials || {};
  const costs = activeBoqSpec.costs || {};

  return (
    <div className="h-full flex flex-col bg-gray-900 text-gray-100 overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 px-4 py-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Calculator className="w-5 h-5 text-emerald-400" />
          <h2 className="font-semibold text-gray-100">Bill of Quantities</h2>
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Plot Input Section */}
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
            <Ruler className="w-4 h-4 text-blue-400" />
            Plot Configuration
          </h3>
          
          <div className="space-y-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Plot Area (sqm)</label>
              <input
                type="number"
                value={plotArea}
                onChange={(e) => handlePlotAreaChange(Number(e.target.value) || 0)}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500 block mb-1">Quality</label>
                <select
                  value={quality}
                  onChange={(e) => handleQualityChange(e.target.value as Quality)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
                >
                  <option value="basic">Basic (₹1800/sqft)</option>
                  <option value="standard">Standard (₹2200/sqft)</option>
                  <option value="premium">Premium (₹2800/sqft)</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Type</label>
                <select
                  value={buildingType}
                  onChange={(e) => setBuildingType(e.target.value as BuildingType)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
                >
                  <option value="apartment">Apartment</option>
                  <option value="villa">Villa</option>
                  <option value="rowhouse">Row House</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleRecalculate}
              className="w-full bg-emerald-600 hover:bg-emerald-500 text-white rounded px-4 py-2 text-sm font-medium transition-colors"
            >
              Recalculate
            </button>
          </div>
        </div>

        {/* Building Specifications */}
        <Section title="Building Specifications" icon={<Building2 className="w-4 h-4 text-emerald-400" />}>
          <DataRow label="Total Floors" value={config?.floors || 0} />
          <DataRow label="Coverage" value={config?.coveragePercent || 0} unit="%" />
          <DataRow label="FAR Limit" value={config?.far || 0} />
          <DataRow label="Achievable Area" value={config?.achievableArea?.toFixed(0) || '0'} unit="sqm" />
          <DataRow label="Ceiling Height" value={heights?.ceilingHeight?.toFixed(1) || '0'} unit="m" />
          <DataRow label="Total Height" value={heights?.totalBuildingHeight?.toFixed(2) || '0'} unit="m" />
        </Section>

        {/* Dimensions */}
        <Section title="Dimensions" icon={<Layers className="w-4 h-4 text-blue-400" />}>
          <div className="text-xs text-gray-500 mb-2">SETBACKS</div>
          <DataRow label="Front" value={setbacks?.front || 0} unit="m" />
          <DataRow label="Back" value={setbacks?.back || 0} unit="m" />
          <DataRow label="Sides" value={`${setbacks?.left || 0}/${setbacks?.right || 0}`} unit="m" />
          
          <div className="text-xs text-gray-500 mt-3 mb-2">BUILDING</div>
          <DataRow label="Width" value={config?.buildingWidth?.toFixed(2) || '0'} unit="m" highlight />
          <DataRow label="Depth" value={config?.buildingDepth?.toFixed(2) || '0'} unit="m" highlight />
          
          <div className="text-xs text-gray-500 mt-3 mb-2">INTERIOR</div>
          <DataRow label="Net Width" value={dimensions?.interiorWidth?.toFixed(2) || '0'} unit="m" />
          <DataRow label="Net Depth" value={dimensions?.interiorDepth?.toFixed(2) || '0'} unit="m" />
          <DataRow label="Per Floor Area" value={dimensions?.interiorArea?.toFixed(1) || '0'} unit="sqm" />
          <DataRow label="Total Area" value={(dimensions?.interiorArea || 0) * (config?.floors || 0)} unit="sqm" highlight />
        </Section>

        {/* Windows & Doors */}
        <Section title="Windows & Doors" icon={<Window className="w-4 h-4 text-cyan-400" />}>
          <div className="text-xs text-gray-500 mb-2">WINDOWS</div>
          <DataRow label="Count per Floor" value={windows?.countPerFloor || 0} />
          <DataRow label="Width" value={windows?.width || 0} unit="m" />
          <DataRow label="Height" value={windows?.height?.toFixed(2) || '0'} unit="m" />
          <DataRow label="Total Glass Area" value={windows?.totalGlassArea?.toFixed(2) || '0'} unit="sqm" />
          
          <div className="text-xs text-gray-500 mt-3 mb-2">DOORS</div>
          <DataRow label="Main Door" value={`${doors?.mainDoor?.width || 0}m × ${doors?.mainDoor?.height || 0}m`} />
          <DataRow label="Room Door" value={`${doors?.roomDoor?.width || 0}m × ${doors?.roomDoor?.height || 0}m`} />
          <DataRow label="Bathroom" value={`${doors?.bathroomDoor?.width || 0}m × ${doors?.bathroomDoor?.height || 0}m`} />
          <DataRow label="Total Door Area" value={doors?.totalDoorArea?.toFixed(2) || '0'} unit="sqm" />
        </Section>

        {/* Material Quantities */}
        <Section title="Material Quantities" icon={<Package className="w-4 h-4 text-amber-400" />}>
          <div className="text-xs text-gray-500 mb-2">STRUCTURAL</div>
          <DataRow label="Concrete" value={materials?.concrete_m3?.toFixed(2) || '0'} unit="m³" highlight />
          <DataRow label="Steel" value={(materials?.steel_kg || 0).toLocaleString()} unit="kg" highlight />
          <DataRow label="Bricks" value={(materials?.bricks_nos || 0).toLocaleString()} unit="nos" />
          
          <div className="text-xs text-gray-500 mt-3 mb-2">FINISHING</div>
          <DataRow label="Cement" value={materials?.cement_bags || 0} unit="bags" />
          <DataRow label="Sand" value={materials?.sand_m3 || 0} unit="m³" />
          <DataRow label="Glass" value={materials?.glass_m2?.toFixed(2) || '0'} unit="m²" />
          <DataRow label="Wood" value={materials?.wood_m3?.toFixed(2) || '0'} unit="m³" />
          <DataRow label="Flooring" value={materials?.flooring_m2?.toFixed(2) || '0'} unit="m²" />
          <DataRow label="Paint" value={materials?.paint_liters || 0} unit="liters" />
        </Section>

        {/* Cost Estimation */}
        <Section title="Cost Estimation" icon={<Calculator className="w-4 h-4 text-emerald-400" />} defaultOpen={true}>
          <div className="bg-gray-750 rounded-lg p-3 mb-3">
            <div className="text-xs text-gray-500 mb-1">Rate per sqft</div>
            <div className="text-2xl font-bold text-emerald-400">{formatINRSafe(costs?.ratePerSqft || 0)}/sqft</div>
          </div>

          <div className="space-y-1">
            <DataRow label="Structure (40%)" value={formatINRSafe(costs?.breakdown?.structure || 0)} />
            <DataRow label="Walls & Finishes (25%)" value={formatINRSafe(costs?.breakdown?.wallsFinishes || 0)} />
            <DataRow label="Doors & Windows (10%)" value={formatINRSafe(costs?.breakdown?.doorsWindows || 0)} />
            <DataRow label="Electrical (8%)" value={formatINRSafe(costs?.breakdown?.electrical || 0)} />
            <DataRow label="Plumbing (7%)" value={formatINRSafe(costs?.breakdown?.plumbing || 0)} />
            <DataRow label="Flooring (5%)" value={formatINRSafe(costs?.breakdown?.flooring || 0)} />
            <DataRow label="Misc (5%)" value={formatINRSafe(costs?.breakdown?.misc || 0)} />
          </div>

          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="text-xs text-gray-500 mb-1">Total Area</div>
            <div className="text-lg font-semibold text-gray-200 mb-3">
              {(costs?.totalAreaSqm || 0).toFixed(0)} sqm ({(costs?.totalAreaSqft || 0).toFixed(0)} sqft)
            </div>

            <div className="bg-emerald-900/30 border border-emerald-700 rounded-lg p-4">
              <div className="text-center">
                <div className="text-xs text-emerald-400 mb-1">TOTAL COST</div>
                <div className="text-3xl font-bold text-emerald-400">{formatINRSafe(costs?.totalINR || 0)}</div>
                <div className="text-lg text-emerald-300/70 mt-1">{formatUSDSafe(costs?.totalUSD || 0)}</div>
              </div>
            </div>

            <div className="mt-3 text-center text-sm text-gray-400">
              Cost per sqft: <span className="text-emerald-400 font-semibold">₹{(costs?.costPerSqft || 0)}/sqft</span>
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
}