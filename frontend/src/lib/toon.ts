/**
 * TOON - Token Oriented Object Notation Parser
 * Compact format for 3D mesh data communication
 */

// Decode TOON format
export function decodeTOON(toonString: string): { meshes: any[], materials: any[] } {
    if (!toonString || !toonString.includes("||")) {
        return { meshes: [], materials: [] };
    }

    const [meshPart, matPart] = toonString.split("||");
    const meshes: any[] = [];
    const materials: any[] = [];

    // Parse meshes
    for (const token of meshPart.split(";")) {
        if (!token.startsWith("MESH|")) continue;
        const parts = token.split("|");
        if (parts.length >= 5) {
            meshes.push({
                position: parts[1].split(",").map(Number),
                scale: parts[2].split(",").map(Number),
                material_id: parts[3],
                component_group: parts[4]
            });
        }
    }

    // Parse materials
    for (const token of matPart.split(";")) {
        if (!token.startsWith("MATERIAL|")) continue;
        const parts = token.split("|");
        if (parts.length >= 5) {
            materials.push({
                material_id: parts[1],
                color_hex: parts[2],
                roughness: parseFloat(parts[3]),
                metallic: parseFloat(parts[4])
            });
        }
    }

    return { meshes, materials };
}

// Material factory - creates proper PBR materials
export function createMaterial(materialId: string, props: {
    color_hex: string;
    roughness: number;
    metallic?: number;
    transmission?: number;
}): THREE.MeshStandardMaterial {
    const color = new THREE.Color(props.color_hex || "#808080");
    const isGlass = materialId.includes("glass") || materialId.includes("transparent");

    const matParams: any = {
        color,
        roughness: props.roughness || 0.5,
        metalness: props.metallic || 0
    };

    if (isGlass) {
        matParams.transparent = true;
        matParams.opacity = props.transmission ? 1 - props.transmission : 0.3;
        matParams.transmission = props.transmission || 0.3;
        matParams.thickness = 0.1;
    }

    return new THREE.MeshStandardMaterial(matParams);
}

// Pre-built material library for performance
const materialLibrary = new Map<string, THREE.MeshStandardMaterial>();

export function getMaterial(materialId: string, props?: any): THREE.MeshStandardMaterial {
    // Check cache
    if (materialLibrary.has(materialId)) {
        return materialLibrary.get(materialId)!;
    }

    // Try to get from props
    const colorHex = props?.color_hex || materialColors[materialId] || "#808080";
    const roughness = props?.roughness ?? materialRoughness[materialId] ?? 0.5;
    const metallic = props?.metallic ?? materialMetallic[materialId] ?? 0;
    const transmission = props?.transmission;

    // Check for glass
    const isGlass = materialId.includes("glass");
    const isMetal = materialId.includes("metal") || materialId.includes("chrome");

    const mat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(colorHex),
        roughness,
        metalness: metallic
    });

    if (isGlass && transmission) {
        mat.transparent = true;
        mat.opacity = 0.3;
        mat.transmission = transmission;
        mat.thickness = 0.1;
    }

    materialLibrary.set(materialId, mat);
    return mat;
}

// Default material mappings
const materialColors: Record<string, string> = {
    concrete: "#9d9d9d",
    plaster_white: "#f5f5f0",
    plaster_beige: "#e8dcc8",
    brick_red: "#a0522d",
    brick_dark: "#654321",
    stone: "#9ea1a3",
    limestone: "#d9d0c1",
    glass_clear: "#d0e8f0",
    glass_tinted: "#405060",
    frame_black: "#1a1a1a",
    frame_white: "#e8e8e8",
    wood_oak: "#8b5a2b",
    wood_dark: "#4a3020",
    metal_dark: "#252525",
    metal_grey: "#707070",
    metal_chrome: "#c0c0c0",
    roof_tiles_red: "#b22222",
    roof_slate: "#4a4a4a",
    roof_metal: "#607080",
    grass: "#4a7c23",
    soil: "#5c4033",
    patio_stone: "#908070"
};

const materialRoughness: Record<string, number> = {
    concrete: 0.85,
    plaster_white: 0.75,
    glass_clear: 0.1,
    glass_tinted: 0.15,
    metal_dark: 0.25,
    metal_chrome: 0.1,
    grass: 0.9
};

const materialMetallic: Record<string, number> = {
    metal_dark: 0.8,
    metal_grey: 0.7,
    metal_chrome: 0.9,
    glass_clear: 0.0
};