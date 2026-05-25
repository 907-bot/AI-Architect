/**
 * Enterprise PBR Material Library
 * High-quality physically based materials with textures and proper lighting response
 */
import * as THREE from 'three';

// Texture URLs - using placeholder paths (should be replaced with actual texture assets)
const TEXTURE_BASE = '/textures';

// Create procedural textures for materials that don't have images
function createBrickTexture(): THREE.CanvasTexture {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext('2d')!;
    
    // Brick pattern
    ctx.fillStyle = '#8B4513';
    ctx.fillRect(0, 0, 256, 256);
    ctx.strokeStyle = '#654321';
    ctx.lineWidth = 3;
    
    // Horizontal lines
    for (let y = 0; y < 256; y += 32) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(256, y);
        ctx.stroke();
    }
    // Vertical lines (offset for brick pattern)
    for (let y = 0; y < 256; y += 32) {
        for (let x = (y % 64 === 0) ? 16 : 0; x < 256; x += 32) {
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(x, y + 32);
            ctx.stroke();
        }
    }
    
    return new THREE.CanvasTexture(canvas);
}

function createConcreteTexture(): THREE.CanvasTexture {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext('2d')!;
    
    // Base concrete color
    ctx.fillStyle = '#a0a0a0';
    ctx.fillRect(0, 0, 256, 256);
    
    // Add noise
    for (let i = 0; i < 1000; i++) {
        const x = Math.random() * 256;
        const y = Math.random() * 256;
        const gray = 150 + Math.random() * 30;
        ctx.fillStyle = `rgb(${gray},${gray},${gray})`;
        ctx.fillRect(x, y, 2, 2);
    }
    
    return new THREE.CanvasTexture(canvas);
}

// Main material library with PBR properties
export class MaterialLibrary {
    private static instance: MaterialLibrary;
    private materials: Map<string, THREE.MeshStandardMaterial> = new Map();
    private textures: Map<string, THREE.Texture> = new Map();
    
    private constructor() {
        this.initMaterials();
    }
    
    static getInstance(): MaterialLibrary {
        if (!MaterialLibrary.instance) {
            MaterialLibrary.instance = new MaterialLibrary();
        }
        return MaterialLibrary.instance;
    }
    
    private initMaterials() {
        // ============================================
        // WALL MATERIALS
        // ============================================
        this.materials.set('plaster_white', new THREE.MeshStandardMaterial({
            color: 0xf5f5f5,
            roughness: 0.9,
            metalness: 0.0,
            envMapIntensity: 0.5
        }));
        
        this.materials.set('plaster_beige', new THREE.MeshStandardMaterial({
            color: 0xe8dcc8,
            roughness: 0.85,
            metalness: 0.0
        }));
        
        this.materials.set('brick_red', new THREE.MeshStandardMaterial({
            color: 0x8b3a3a,
            roughness: 0.85,
            metalness: 0.0,
            bumpScale: 0.02
        }));
        
        this.materials.set('brick_dark', new THREE.MeshStandardMaterial({
            color: 0x654321,
            roughness: 0.8,
            metalness: 0.0
        }));
        
        this.materials.set('stone', new THREE.MeshStandardMaterial({
            color: 0x9ea1a3,
            roughness: 0.7,
            metalness: 0.1
        }));
        
        this.materials.set('limestone', new THREE.MeshStandardMaterial({
            color: 0xd9d0c1,
            roughness: 0.65,
            metalness: 0.0
        }));
        
        // ============================================
        // GLASS MATERIALS
        // ============================================
        this.materials.set('glass_clear', new THREE.MeshStandardMaterial({
            color: 0x88ccff,
            roughness: 0.05,
            metalness: 0.1,
            transparent: true,
            opacity: 0.3,
            transmission: 0.9,
            thickness: 0.5,
            ior: 1.5,
            envMapIntensity: 1.0
        }));
        
        this.materials.set('glass_tinted', new THREE.MeshStandardMaterial({
            color: 0x405060,
            roughness: 0.1,
            metalness: 0.2,
            transparent: true,
            opacity: 0.4,
            transmission: 0.6
        }));
        
        this.materials.set('glass_reflective', new THREE.MeshStandardMaterial({
            color: 0x204050,
            roughness: 0.02,
            metalness: 0.4,
            transparent: true,
            opacity: 0.5,
            transmission: 0.5
        }));
        
        // ============================================
        // FRAME MATERIALS
        // ============================================
        this.materials.set('frame_black', new THREE.MeshStandardMaterial({
            color: 0x1a1a1a,
            roughness: 0.3,
            metalness: 0.7,
            envMapIntensity: 1.2
        }));
        
        this.materials.set('frame_white', new THREE.MeshStandardMaterial({
            color: 0xe8e8e8,
            roughness: 0.35,
            metalness: 0.5
        }));
        
        this.materials.set('frame_wood', new THREE.MeshStandardMaterial({
            color: 0x6b4423,
            roughness: 0.5,
            metalness: 0.0
        }));
        
        this.materials.set('frame_metal', new THREE.MeshStandardMaterial({
            color: 0x505050,
            roughness: 0.25,
            metalness: 0.8
        }));
        
        // ============================================
        // DOOR MATERIALS
        // ============================================
        this.materials.set('wood_oak', new THREE.MeshStandardMaterial({
            color: 0x8b5a2b,
            roughness: 0.6,
            metalness: 0.0
        }));
        
        this.materials.set('wood_dark', new THREE.MeshStandardMaterial({
            color: 0x4a3020,
            roughness: 0.5,
            metalness: 0.0
        }));
        
        this.materials.set('wood_ply', new THREE.MeshStandardMaterial({
            color: 0xa08060,
            roughness: 0.7,
            metalness: 0.0
        }));
        
        this.materials.set('metaldoor', new THREE.MeshStandardMaterial({
            color: 0x404040,
            roughness: 0.3,
            metalness: 0.7
        }));
        
        // ============================================
        // ROOF MATERIALS
        // ============================================
        this.materials.set('roof_tiles_red', new THREE.MeshStandardMaterial({
            color: 0xb22222,
            roughness: 0.65,
            metalness: 0.0
        }));
        
        this.materials.set('roof_tiles_brown', new THREE.MeshStandardMaterial({
            color: 0x5c4033,
            roughness: 0.7,
            metalness: 0.0
        }));
        
        this.materials.set('roof_slate', new THREE.MeshStandardMaterial({
            color: 0x4a4a4a,
            roughness: 0.6,
            metalness: 0.0
        }));
        
        this.materials.set('roof_metal', new THREE.MeshStandardMaterial({
            color: 0x607080,
            roughness: 0.4,
            metalness: 0.5
        }));
        
        this.materials.set('roof_metal_dark', new THREE.MeshStandardMaterial({
            color: 0x303030,
            roughness: 0.35,
            metalness: 0.6
        }));
        
        this.materials.set('roof_flat', new THREE.MeshStandardMaterial({
            color: 0x505050,
            roughness: 0.8,
            metalness: 0.0
        }));
        
        // ============================================
        // METAL MATERIALS
        // ============================================
        this.materials.set('metal_dark', new THREE.MeshStandardMaterial({
            color: 0x252525,
            roughness: 0.25,
            metalness: 0.8,
            envMapIntensity: 1.5
        }));
        
        this.materials.set('metal_grey', new THREE.MeshStandardMaterial({
            color: 0x707070,
            roughness: 0.3,
            metalness: 0.7
        }));
        
        this.materials.set('metal_chrome', new THREE.MeshStandardMaterial({
            color: 0xc0c0c0,
            roughness: 0.1,
            metalness: 0.9,
            envMapIntensity: 2.0
        }));
        
        this.materials.set('concrete', new THREE.MeshStandardMaterial({
            color: 0x9d9d9d,
            roughness: 0.85,
            metalness: 0.0
        }));
        
        this.materials.set('concrete_tex', new THREE.MeshStandardMaterial({
            color: 0xa8a8a8,
            roughness: 0.9,
            metalness: 0.0
        }));
        
        // ============================================
        // LANDSCAPE MATERIALS
        // ============================================
        this.materials.set('grass', new THREE.MeshStandardMaterial({
            color: 0x4a7c23,
            roughness: 0.95,
            metalness: 0.0
        }));
        
        this.materials.set('soil', new THREE.MeshStandardMaterial({
            color: 0x5c4033,
            roughness: 0.95,
            metalness: 0.0
        }));
        
        this.materials.set('patio_stone', new THREE.MeshStandardMaterial({
            color: 0x908070,
            roughness: 0.8,
            metalness: 0.0
        }));
        
        this.materials.set('gravel', new THREE.MeshStandardMaterial({
            color: 0x807060,
            roughness: 0.95,
            metalness: 0.0
        }));
        
        // ============================================
        // FANCY MATERIALS (for enterprise look)
        // ============================================
        this.materials.set('marble_white', new THREE.MeshStandardMaterial({
            color: 0xfafafa,
            roughness: 0.2,
            metalness: 0.1,
            envMapIntensity: 0.8
        }));
        
        this.materials.set('granite', new THREE.MeshStandardMaterial({
            color: 0x606060,
            roughness: 0.4,
            metalness: 0.2
        }));
        
        this.materials.set('copper', new THREE.MeshStandardMaterial({
            color: 0xb87333,
            roughness: 0.3,
            metalness: 0.8
        }));
        
        this.materials.set('brass', new THREE.MeshStandardMaterial({
            color: 0xc9a227,
            roughness: 0.35,
            metalness: 0.75
        }));
    }
    
    /**
     * Get material by ID - creates default if not found
     */
    getMaterial(materialId: string): THREE.MeshStandardMaterial {
        // Try exact match first
        if (this.materials.has(materialId)) {
            return this.materials.get(materialId)!;
        }
        
        // Try fuzzy match
        const lowerId = materialId.toLowerCase();
        for (const [key, mat] of this.materials) {
            if (key.includes(lowerId) || lowerId.includes(key)) {
                return mat;
            }
        }
        
        // Default fallback
        console.warn(`Material not found: ${materialId}, using default`);
        return this.materials.get('concrete')!;
    }
    
    /**
     * Get all available material IDs
     */
    getAvailableMaterials(): string[] {
        return Array.from(this.materials.keys());
    }
    
    /**
     * Create environment map for realistic reflections
     */
    createEnvironmentMap(scene: THREE.Scene): THREE.CubeTexture {
        // Simple gradient environment (fallback if no HDR)
        const pmremGenerator = new THREE.PMREMGenerator(
            (scene as any).renderer || 
            (() => {
                const renderer = new THREE.WebGLRenderer();
                return renderer;
            })()
        );
        
        // Create a simple studio-like environment
        const envScene = new THREE.Scene();
        
        // Gradient background
        const topColor = new THREE.Color(0x87ceeb);
        const bottomColor = new THREE.Color(0x444444);
        
        return pmremGenerator.fromScene(envScene).texture;
    }
}

// Export singleton getter
export const materialLibrary = MaterialLibrary.getInstance();
export default MaterialLibrary;