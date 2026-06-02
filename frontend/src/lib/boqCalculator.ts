/**
 * BOQ (Bill of Quantities) Calculator
 * Dynamic building measurements and cost estimation based on NBC 2016 standards
 */

// Types
export interface BuildingConfig {
  plotArea: number;           // sqm
  plotWidth: number;          // m
  plotDepth: number;          // m
  floors: number;
  coveragePercent: number;
  buildingWidth: number;      // m
  buildingDepth: number;      // m
  far: number;
  achievableArea: number;     // sqm
}

export interface HeightConfig {
  ceilingHeight: number;      // m
  slabThickness: number;      // m
  parapetHeight: number;      // m
  totalFloorHeight: number;   // m
  totalBuildingHeight: number; // m
}

export interface DimensionConfig {
  exteriorWidth: number;      // m
  exteriorDepth: number;      // m
  interiorWidth: number;      // m
  interiorDepth: number;      // m
  exteriorArea: number;       // sqm (per floor)
  interiorArea: number;       // sqm (per floor)
}

export interface SetbackConfig {
  front: number;              // m
  back: number;               // m
  left: number;               // m
  right: number;              // m
  buildableWidth: number;     // m
  buildableDepth: number;     // m
}

export interface WindowConfig {
  countPerFloor: number;
  width: number;              // m
  height: number;             // m
  totalGlassArea: number;      // sqm
  frameLength: number;         // m
}

export interface DoorConfig {
  mainDoor: { width: number; height: number; };
  roomDoor: { width: number; height: number; };
  bathroomDoor: { width: number; height: number; };
  totalDoorArea: number;      // sqm
}

export interface MaterialQuantities {
  concrete_m3: number;
  steel_kg: number;
  bricks_nos: number;
  cement_bags: number;
  sand_m3: number;
  glass_m2: number;
  wood_m3: number;
  flooring_m2: number;
  paint_liters: number;
}

export interface CostBreakdown {
  structure: number;
  wallsFinishes: number;
  doorsWindows: number;
  electrical: number;
  plumbing: number;
  flooring: number;
  misc: number;
}

export interface CostEstimate {
  ratePerSqft: number;
  ratePerSqm: number;
  totalAreaSqft: number;
  totalAreaSqm: number;
  costPerSqft: number;
  totalINR: number;
  totalUSD: number;
  breakdown: CostBreakdown;
}

export interface BOQSpec {
  config: BuildingConfig;
  heights: HeightConfig;
  dimensions: DimensionConfig;
  setbacks: SetbackConfig;
  windows: WindowConfig;
  doors: DoorConfig;
  materials: MaterialQuantities;
  costs: CostEstimate;
  buildingType: 'apartment' | 'villa' | 'rowhouse';
  quality: 'basic' | 'standard' | 'premium';
}

// Constants
const SQFT_TO_SQM = 0.0929;
const SQMT_TO_SQFT = 10.764;
const INR_TO_USD = 83; // Approximate rate

const WALL_THICKNESS_EXTERIOR = 0.3; // m
const WALL_THICKNESS_INTERIOR = 0.15; // m

const RATES_PER_SQFT = {
  basic: 1800,
  standard: 2200,
  premium: 2800,
};

const COST_PERCENTAGES = {
  structure: 0.40,
  wallsFinishes: 0.25,
  doorsWindows: 0.10,
  electrical: 0.08,
  plumbing: 0.07,
  flooring: 0.05,
  misc: 0.05,
};

/**
 * Calculate building configuration from plot size
 */
export function calculateBuildingConfig(plotAreaSqM: number): BuildingConfig {
  // Handle invalid input
  const safeArea = isNaN(plotAreaSqM) || plotAreaSqM <= 0 ? 500 : plotAreaSqM;
  
  // Estimate plot dimensions (assuming roughly square/rectangular)
  const aspectRatio = 0.8; // width/depth ratio
  const plotWidth = Math.sqrt(safeArea * aspectRatio);
  const plotDepth = safeArea / plotWidth;

  // Determine floors and coverage based on plot size
  let floors: number;
  let coveragePercent: number;
  let far: number;

  if (plotAreaSqM <= 200) {
    floors = 1;
    coveragePercent = 60;
    far = 1.5;
  } else if (plotAreaSqM <= 400) {
    floors = 2;
    coveragePercent = 55;
    far = 2.5;
  } else if (plotAreaSqM <= 600) {
    floors = 2;
    coveragePercent = 50;
    far = 3.0;
  } else if (plotAreaSqM <= 900) {
    floors = 3;
    coveragePercent = 45;
    far = 3.5;
  } else if (plotAreaSqM <= 1200) {
    floors = 4;
    coveragePercent = 40;
    far = 3.5;
  } else {
    floors = 5;
    coveragePercent = 35;
    far = 3.5;
  }

  // Calculate building dimensions
  const buildableWidth = plotWidth - 2; // 1m setback each side
  const buildableDepth = plotDepth - 2.5; // front/back setbacks

  // Calculate max footprint
  const maxFootprint = (coveragePercent / 100) * plotAreaSqM;

  // Determine building width/depth to maximize coverage
  let buildingWidth = Math.min(buildableWidth, Math.sqrt(maxFootprint * (plotWidth / plotDepth)));
  let buildingDepth = maxFootprint / buildingWidth;

  // Ensure building fits in plot
  buildingWidth = Math.min(buildingWidth, buildableWidth);
  buildingDepth = Math.min(buildingDepth, buildableDepth);

  // Calculate achievable area
  const achievableArea = buildingWidth * buildingDepth * floors;

  return {
    plotArea: plotAreaSqM,
    plotWidth: Math.round(plotWidth * 100) / 100,
    plotDepth: Math.round(plotDepth * 100) / 100,
    floors,
    coveragePercent,
    buildingWidth: Math.round(buildingWidth * 100) / 100,
    buildingDepth: Math.round(buildingDepth * 100) / 100,
    far,
    achievableArea: Math.round(achievableArea * 100) / 100,
  };
}

/**
 * Calculate heights based on floor count and quality
 */
export function calculateHeights(floors: number, ceilingHeight: number = 3.0): HeightConfig {
  const slabThickness = 0.15; // m
  const parapetHeight = 1.0; // m (for rooftop)
  const totalFloorHeight = ceilingHeight + slabThickness;

  return {
    ceilingHeight,
    slabThickness,
    parapetHeight,
    totalFloorHeight,
    totalBuildingHeight: (totalFloorHeight * floors) + parapetHeight,
  };
}

/**
 * Calculate dimensions (exterior and interior)
 */
export function calculateDimensions(buildingWidth: number, buildingDepth: number): DimensionConfig {
  const exteriorWidth = buildingWidth + (2 * WALL_THICKNESS_EXTERIOR);
  const exteriorDepth = buildingDepth + (2 * WALL_THICKNESS_EXTERIOR);
  const interiorWidth = buildingWidth - (2 * WALL_THICKNESS_INTERIOR);
  const interiorDepth = buildingDepth - (2 * WALL_THICKNESS_INTERIOR);

  return {
    exteriorWidth: Math.round(exteriorWidth * 100) / 100,
    exteriorDepth: Math.round(exteriorDepth * 100) / 100,
    interiorWidth: Math.round(interiorWidth * 100) / 100,
    interiorDepth: Math.round(interiorDepth * 100) / 100,
    exteriorArea: buildingWidth * buildingDepth,
    interiorArea: interiorWidth * interiorDepth,
  };
}

/**
 * Calculate setbacks
 */
export function calculateSetbacks(plotWidth: number, plotDepth: number, buildingWidth: number, buildingDepth: number): SetbackConfig {
  const front = 1.5;
  const back = 1.0;
  const side = 0.5;
  
  const buildableWidth = plotWidth - (2 * side);
  const buildableDepth = plotDepth - front - back;

  return {
    front,
    back,
    left: side,
    right: side,
    buildableWidth: Math.round(buildableWidth * 100) / 100,
    buildableDepth: Math.round(buildableDepth * 100) / 100,
  };
}

/**
 * Calculate windows
 */
export function calculateWindows(
  buildingWidth: number,
  buildingDepth: number,
  ceilingHeight: number
): WindowConfig {
  const windowHeight = ceilingHeight * 0.5;
  const windowWidth = 1.2; // standard window
  
  // Windows on front and back walls
  const windowsPerSide = Math.floor(buildingWidth / 3);
  const countPerFloor = windowsPerSide * 2; // front + back
  
  const totalGlassArea = countPerFloor * (windowWidth * windowHeight);
  const frameLength = countPerFloor * (2 * (windowWidth + windowHeight));

  return {
    countPerFloor,
    width: windowWidth,
    height: Math.round(windowHeight * 100) / 100,
    totalGlassArea: Math.round(totalGlassArea * 100) / 100,
    frameLength: Math.round(frameLength * 100) / 100,
  };
}

/**
 * Calculate doors
 */
export function calculateDoors(floors: number): DoorConfig {
  const mainDoor = { width: 0.9, height: 2.1 };
  const roomDoor = { width: 0.8, height: 2.0 };
  const bathroomDoor = { width: 0.7, height: 2.0 };
  
  // 1 main door per floor, 3 room doors per floor, 1 bathroom per floor
  const totalDoorArea = floors * (
    (mainDoor.width * mainDoor.height) +
    (3 * roomDoor.width * roomDoor.height) +
    (bathroomDoor.width * bathroomDoor.height)
  );

  return {
    mainDoor,
    roomDoor,
    bathroomDoor,
    totalDoorArea: Math.round(totalDoorArea * 100) / 100,
  };
}

/**
 * Calculate material quantities
 */
export function calculateMaterialQuantities(
  config: BuildingConfig,
  dimensions: DimensionConfig,
  heights: HeightConfig
): MaterialQuantities {
  const floors = config.floors;
  const footprint = config.buildingWidth * config.buildingDepth;
  
  // Foundation concrete (0.5m depth, 1.2m wide strip)
  const foundationConcrete = footprint * 0.5 * 1.2;
  
  // Floor slabs (including roof)
  const slabConcrete = footprint * heights.slabThickness * (floors + 1);
  
  // Columns (approximate)
  const columnConcrete = floors * 0.5 * 0.5 * 3.5 * 8; // 8 columns
  const totalConcrete = foundationConcrete + slabConcrete + columnConcrete;

  // Steel reinforcement (100 kg per cubic meter of concrete)
  const steel_kg = totalConcrete * 100;

  // Brick walls (exterior + interior)
  const exteriorWallArea = 2 * (dimensions.exteriorWidth + dimensions.exteriorDepth) * heights.ceilingHeight * floors;
  const interiorWallArea = 2 * (dimensions.interiorWidth + dimensions.interiorDepth) * heights.ceilingHeight * floors * 0.7; // 70% of interior
  const totalWallArea = exteriorWallArea + interiorWallArea;
  
  // Bricks (500 per sqm, accounting for 20% wastage)
  const bricks_nos = Math.ceil(totalWallArea * 500 * 1.2);

  // Cement (0.4 bags per sqm of wall)
  const cement_bags = Math.ceil(totalWallArea * 0.4);

  // Sand (0.02 cubic meters per sqm of wall)
  const sand_m3 = Math.round(totalWallArea * 0.02 * 100) / 100;

  // Glass area from windows
  const glass_m2 = dimensions.exteriorArea * 0.15; // 15% of floor area for windows

  // Wood for doors and frames
  const wood_m3 = floors * 0.15; // 0.15 cubic meters per floor

  // Flooring
  const flooring_m2 = dimensions.interiorArea * floors;

  // Paint (0.2 liters per sqm, 2 coats)
  const paint_liters = Math.ceil(totalWallArea * 0.2);

  return {
    concrete_m3: Math.round(totalConcrete * 100) / 100,
    steel_kg: Math.round(steel_kg),
    bricks_nos,
    cement_bags,
    sand_m3,
    glass_m2: Math.round(glass_m2 * 100) / 100,
    wood_m3: Math.round(wood_m3 * 100) / 100,
    flooring_m2: Math.round(flooring_m2 * 100) / 100,
    paint_liters,
  };
}

/**
 * Calculate costs
 */
export function calculateCosts(
  totalAreaSqm: number,
  quality: 'basic' | 'standard' | 'premium'
): CostEstimate {
  const ratePerSqft = RATES_PER_SQFT[quality];
  const ratePerSqm = ratePerSqft / SQFT_TO_SQM;
  const totalAreaSqft = totalAreaSqm * SQMT_TO_SQFT;
  
  const total = totalAreaSqft * ratePerSqft;
  
  const breakdown: CostBreakdown = {
    structure: Math.round(total * COST_PERCENTAGES.structure),
    wallsFinishes: Math.round(total * COST_PERCENTAGES.wallsFinishes),
    doorsWindows: Math.round(total * COST_PERCENTAGES.doorsWindows),
    electrical: Math.round(total * COST_PERCENTAGES.electrical),
    plumbing: Math.round(total * COST_PERCENTAGES.plumbing),
    flooring: Math.round(total * COST_PERCENTAGES.flooring),
    misc: Math.round(total * COST_PERCENTAGES.misc),
  };

  return {
    ratePerSqft,
    ratePerSqm: Math.round(ratePerSqm),
    totalAreaSqft: Math.round(totalAreaSqft * 100) / 100,
    totalAreaSqm: Math.round(totalAreaSqm * 100) / 100,
    costPerSqft: ratePerSqft,
    totalINR: Math.round(total),
    totalUSD: Math.round(total / INR_TO_USD),
    breakdown,
  };
}

/**
 * Full BOQ calculation
 */
export function calculateBOQ(
  plotAreaSqM: number,
  quality: 'basic' | 'standard' | 'premium' = 'standard',
  ceilingHeight: number = 3.0
): BOQSpec {
  // Ensure valid input
  const safeArea = Math.max(plotAreaSqM, 100); // Minimum 100 sqm
  const safeCeiling = Math.max(ceilingHeight, 2.5); // Minimum 2.5m
  
  const config = calculateBuildingConfig(safeArea);
  const heights = calculateHeights(config.floors, safeCeiling);
  const dimensions = calculateDimensions(config.buildingWidth, config.buildingDepth);
  const setbacks = calculateSetbacks(config.plotWidth, config.plotDepth, config.buildingWidth, config.buildingDepth);
  const windows = calculateWindows(config.buildingWidth, config.buildingDepth, safeCeiling);
  const doors = calculateDoors(config.floors);
  const materials = calculateMaterialQuantities(config, dimensions, heights);
  const costs = calculateCosts(config.achievableArea, quality);

  return {
    config,
    heights,
    dimensions,
    setbacks,
    windows,
    doors,
    materials,
    costs,
    buildingType: 'apartment',
    quality,
  };
}

/**
 * Format number to Indian currency format (lakhs/crores)
 */
export function formatINR(amount: number): string {
  if (amount >= 10000000) {
    return `₹${(amount / 10000000).toFixed(2)} Cr`;
  } else if (amount >= 100000) {
    return `₹${(amount / 100000).toFixed(2)} L`;
  }
  return `₹${amount.toLocaleString('en-IN')}`;
}

/**
 * Format USD
 */
export function formatUSD(amount: number): string {
  return `$${amount.toLocaleString('en-US')}`;
}

/**
 * Get ceiling height based on quality
 */
export function getCeilingHeight(quality: 'basic' | 'standard' | 'premium'): number {
  switch (quality) {
    case 'basic':
      return 2.8;
    case 'standard':
      return 3.0;
    case 'premium':
      return 3.2;
  }
}