"use client";
import React, { useState, useEffect } from "react";
import { useStore } from "@/lib/store";
import {
  Calculator, Ruler, Home, Layers, DoorOpen, Window, Hammer,
  Zap, Droplets, Square, Paintbrush, ChevronDown, ChevronRight,
  IndianRupee, DollarSign, Building2, Package
} from "lucide-react";
import { formatINR, formatUSD } from "@/lib/boqCalculator";

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

export default function BOQPanel() {
  const { plotWidth, plotDepth, boqSpec, calculateBoq } = useStore();
  
  const [plotArea, setPlotArea] = useState<number>(plotWidth * plotDepth || 500);
  const [quality, setQuality] = useState<Quality>("standard");
  const [buildingType, setBuildingType] = useState<BuildingType>("apartment");

  // Auto-calculate when plot size changes
  useEffect(() => {
    const area = plotWidth * plotDepth;
    if (area > 0) {
      setPlotArea(area);
      calculateBoq(area, quality);
    }
  }, [plotWidth, plotDepth, quality, calculateBoq]);

  // Recalculate when user changes inputs
  const handleRecalculate = () => {
    calculateBoq(plotArea, quality);
  };

  if (!boqSpec) {
    return (
      <div className="p-6 text-center text-gray-400">
        <Calculator className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>Loading BOQ calculations...</p>
      </div>
    );
  }

  const { config, heights, dimensions, setbacks, windows, doors, materials, costs } = boqSpec;

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
                onChange={(e) => setPlotArea(Number(e.target.value))}
                onBlur={handleRecalculate}
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500 block mb-1">Quality</label>
                <select
                  value={quality}
                  onChange={(e) => {
                    setQuality(e.target.value as Quality);
                    setTimeout(handleRecalculate, 0);
                  }}
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
          <DataRow label="Total Floors" value={config.floors} />
          <DataRow label="Coverage" value={config.coveragePercent} unit="%" />
          <DataRow label="FAR Limit" value={config.far} />
          <DataRow label="Achievable Area" value={config.achievableArea.toFixed(0)} unit="sqm" />
          <DataRow label="Ceiling Height" value={heights.ceilingHeight} unit="m" />
          <DataRow label="Total Height" value={heights.totalBuildingHeight.toFixed(2)} unit="m" />
        </Section>

        {/* Dimensions */}
        <Section title="Dimensions" icon={<Layers className="w-4 h-4 text-blue-400" />}>
          <div className="text-xs text-gray-500 mb-2">SETBACKS</div>
          <DataRow label="Front" value={setbacks.front} unit="m" />
          <DataRow label="Back" value={setbacks.back} unit="m" />
          <DataRow label="Sides" value={`${setbacks.left}/${setbacks.right}`} unit="m" />
          
          <div className="text-xs text-gray-500 mt-3 mb-2">BUILDING</div>
          <DataRow label="Width" value={config.buildingWidth} unit="m" highlight />
          <DataRow label="Depth" value={config.buildingDepth} unit="m" highlight />
          
          <div className="text-xs text-gray-500 mt-3 mb-2">INTERIOR</div>
          <DataRow label="Net Width" value={dimensions.interiorWidth} unit="m" />
          <DataRow label="Net Depth" value={dimensions.interiorDepth} unit="m" />
          <DataRow label="Per Floor Area" value={dimensions.interiorArea.toFixed(1)} unit="sqm" />
          <DataRow label="Total Area" value={dimensions.interiorArea * config.floors} unit="sqm" highlight />
        </Section>

        {/* Windows & Doors */}
        <Section title="Windows & Doors" icon={<Window className="w-4 h-4 text-cyan-400" />}>
          <div className="text-xs text-gray-500 mb-2">WINDOWS</div>
          <DataRow label="Count per Floor" value={windows.countPerFloor} />
          <DataRow label="Width" value={windows.width} unit="m" />
          <DataRow label="Height" value={windows.height} unit="m" />
          <DataRow label="Total Glass Area" value={windows.totalGlassArea.toFixed(2)} unit="sqm" />
          
          <div className="text-xs text-gray-500 mt-3 mb-2">DOORS</div>
          <DataRow label="Main Door" value={`${doors.mainDoor.width}m × ${doors.mainDoor.height}m`} />
          <DataRow label="Room Door" value={`${doors.roomDoor.width}m × ${doors.roomDoor.height}m`} />
          <DataRow label="Bathroom" value={`${doors.bathroomDoor.width}m × ${doors.bathroomDoor.height}m`} />
          <DataRow label="Total Door Area" value={doors.totalDoorArea.toFixed(2)} unit="sqm" />
        </Section>

        {/* Material Quantities */}
        <Section title="Material Quantities" icon={<Package className="w-4 h-4 text-amber-400" />}>
          <div className="text-xs text-gray-500 mb-2">STRUCTURAL</div>
          <DataRow label="Concrete" value={materials.concrete_m3} unit="m³" highlight />
          <DataRow label="Steel" value={materials.steel_kg.toLocaleString()} unit="kg" highlight />
          <DataRow label="Bricks" value={materials.bricks_nos.toLocaleString()} unit="nos" />
          
          <div className="text-xs text-gray-500 mt-3 mb-2">FINISHING</div>
          <DataRow label="Cement" value={materials.cement_bags} unit="bags" />
          <DataRow label="Sand" value={materials.sand_m3} unit="m³" />
          <DataRow label="Glass" value={materials.glass_m2} unit="m²" />
          <DataRow label="Wood" value={materials.wood_m3} unit="m³" />
          <DataRow label="Flooring" value={materials.flooring_m2} unit="m²" />
          <DataRow label="Paint" value={materials.paint_liters} unit="liters" />
        </Section>

        {/* Cost Estimation */}
        <Section title="Cost Estimation" icon={<Calculator className="w-4 h-4 text-emerald-400" />} defaultOpen={true}>
          <div className="bg-gray-750 rounded-lg p-3 mb-3">
            <div className="text-xs text-gray-500 mb-1">Rate per sqft</div>
            <div className="text-2xl font-bold text-emerald-400">{formatINR(costs.ratePerSqft)}/sqft</div>
          </div>

          <div className="space-y-1">
            <DataRow label="Structure (40%)" value={formatINR(costs.breakdown.structure)} />
            <DataRow label="Walls & Finishes (25%)" value={formatINR(costs.breakdown.wallsFinishes)} />
            <DataRow label="Doors & Windows (10%)" value={formatINR(costs.breakdown.doorsWindows)} />
            <DataRow label="Electrical (8%)" value={formatINR(costs.breakdown.electrical)} />
            <DataRow label="Plumbing (7%)" value={formatINR(costs.breakdown.plumbing)} />
            <DataRow label="Flooring (5%)" value={formatINR(costs.breakdown.flooring)} />
            <DataRow label="Misc (5%)" value={formatINR(costs.breakdown.misc)} />
          </div>

          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="text-xs text-gray-500 mb-1">Total Area</div>
            <div className="text-lg font-semibold text-gray-200 mb-3">
              {costs.totalAreaSqm.toFixed(0)} sqm ({costs.totalAreaSqft.toFixed(0)} sqft)
            </div>

            <div className="bg-emerald-900/30 border border-emerald-700 rounded-lg p-4">
              <div className="text-center">
                <div className="text-xs text-emerald-400 mb-1">TOTAL COST</div>
                <div className="text-3xl font-bold text-emerald-400">{formatINR(costs.totalINR)}</div>
                <div className="text-lg text-emerald-300/70 mt-1">{formatUSD(costs.totalUSD)}</div>
              </div>
            </div>

            <div className="mt-3 text-center text-sm text-gray-400">
              Cost per sqft: <span className="text-emerald-400 font-semibold">₹{costs.costPerSqft}/sqft</span>
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
}