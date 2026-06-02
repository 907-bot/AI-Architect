"use client";
import React, { useState, useEffect, useCallback } from "react";
import { useStore } from "@/lib/store";
import { Calculator, Ruler, Building2, Layers, Window, Package } from "lucide-react";

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
          <DataRow label="Total Floors" value={calcData?.floors || 0} />
          <DataRow label="Coverage" value={calcData?.coverage || 0} unit="%" />
          <DataRow label="Building Width" value={(calcData?.buildingWidth || 0).toFixed(2)} unit="m" />
          <DataRow label="Building Depth" value={(calcData?.buildingDepth || 0).toFixed(2)} unit="m" />
          <DataRow label="Total Area" value={(calcData?.totalArea || 0).toFixed(0)} unit="sqm" />
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