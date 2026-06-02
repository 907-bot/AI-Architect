"use client";
import React, { useState, useEffect, useCallback } from "react";
import { useStore } from "@/lib/store";
import {
  Calculator, Ruler, Home, Layers, DoorOpen, AppWindow, Hammer,
  Zap, Droplets, Square, Paintbrush, ChevronDown, ChevronRight,
  IndianRupee, DollarSign, Building2, Package
} from "lucide-react";
import { formatINR, formatUSD } from "@/lib/boqCalculator";

type Quality = "basic" | "standard" | "premium";

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
      </button>
      {isOpen && <div className="p-4 space-y-2">{children}</div>}
    </div>
  );
}

function DataRow({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div className="flex justify-between items-center py-1">
      <span className="text-gray-400 text-sm">{label}</span>
      <span className="text-sm font-mono text-gray-200">
        {value}{unit && <span className="text-gray-500 ml-1">{unit}</span>}
      </span>
    </div>
  );
}

function formatINR(amount: number): string {
  if (typeof amount !== 'number' || isNaN(amount)) return '₹0';
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)} Cr`;
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)} L`;
  return `₹${amount.toLocaleString('en-IN')}`;
}

function formatUSD(amount: number): string {
  if (typeof amount !== 'number' || isNaN(amount)) return '$0';
  return `$${amount.toLocaleString('en-US')}`;
}

// Simple calculation functions inline to avoid module issues
function calculateSimple(area: number, quality: Quality) {
  const rate = quality === 'basic' ? 1800 : quality === 'standard' ? 2200 : 2800;
  const sqft = area * 10.764;
  const total = sqft * rate;
  return {
    floors: area < 400 ? 2 : area < 900 ? 3 : 4,
    coverage: 45,
    buildingWidth: Math.sqrt(area * 0.4),
    buildingDepth: Math.sqrt(area * 0.4),
    totalArea: area,
    totalCost: total,
    ratePerSqft: rate,
  };
}

export default function BOQPanel() {
  const [initialized, setInitialized] = useState(false);
  const [quality, setQuality] = useState<Quality>("standard");
  const [calcData, setCalcData] = useState<any>(null);

  useEffect(() => {
    setInitialized(true);
    const data = calculateSimple(600, quality);
    setCalcData(data);
  }, []);

  const handleQualityChange = (q: Quality) => {
    setQuality(q);
    const data = calculateSimple(600, q);
    setCalcData(data);
  };

  if (!initialized) {
    return (
      <div className="h-full flex flex-col bg-gray-900 text-gray-100 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Calculator className="w-5 h-5 text-emerald-400" />
          <h2 className="font-semibold">Bill of Quantities</h2>
        </div>
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gray-900 text-gray-100 overflow-hidden">
      <div className="flex-shrink-0 px-4 py-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Calculator className="w-5 h-5 text-emerald-400" />
          <h2 className="font-semibold">Bill of Quantities</h2>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Quality Selector */}
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <label className="text-xs text-gray-500 block mb-2">Quality Tier</label>
          <select
            value={quality}
            onChange={(e) => handleQualityChange(e.target.value as Quality)}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100"
          >
            <option value="basic">Basic (₹1800/sqft)</option>
            <option value="standard">Standard (₹2200/sqft)</option>
            <option value="premium">Premium (₹2800/sqft)</option>
          </select>
        </div>

        {/* Specifications */}
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
        <Section title="Windows & Doors" icon={<AppWindow className="w-4 h-4 text-cyan-400" />}>
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
            <div className="text-2xl font-bold text-emerald-400">
              {formatINR(calcData?.ratePerSqft || 0)}/sqft
            </div>
          </div>

          <div className="bg-emerald-900/30 border border-emerald-700 rounded-lg p-4">
            <div className="text-center">
              <div className="text-xs text-emerald-400 mb-1">TOTAL COST</div>
              <div className="text-3xl font-bold text-emerald-400">
                {formatINR(calcData?.totalCost || 0)}
              </div>
              <div className="text-lg text-emerald-300/70 mt-1">
                {formatUSD((calcData?.totalCost || 0) / 83)}
              </div>
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
}