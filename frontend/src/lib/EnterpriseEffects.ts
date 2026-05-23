/**
 * Enterprise Post-Processing Effects
 * SSAO, Bloom, Ambient Occlusion for realistic rendering
 */
import { EffectComposer, RenderPass, SSAOPass, BloomPass, UnrealBloomPass } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { FXAAShader } from 'three/examples/jsm/shaders/FXAAShader.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';

/**
 * Enterprise Renderer Setup
 * Adds professional post-processing and lighting
 */
export class EnterpriseRenderer {
    private composer: EffectComposer | null = null;
    private scene: THREE.Scene;
    private camera: THREE.OrthographicCamera;
    private renderer: THREE.WebGLRenderer;
    
    // Post-processing passes
    private ssaoPass: SSAOPass | null = null;
    private bloomPass: BloomPass | null = null;
    private fxaaPass: ShaderPass | null = null;
    
    constructor(
        scene: THREE.Scene, 
        camera: THREE.OrthographicCamera,
        renderer: THREE.WebGLRenderer
    ) {
        this.scene = scene;
        this.camera = camera;
        this.renderer = renderer;
        this.setupPostProcessing();
    }
    
    private setupPostProcessing() {
        const width = window.innerWidth;
        const height = window.innerHeight;
        
        // Create composer
        this.composer = new EffectComposer(this.renderer);
        
        // Add render pass
        const renderPass = new RenderPass(this.scene, this.camera);
        this.composer.addPass(renderPass);
        
        // =============================================
        // SSAO (Screen Space Ambient Occlusion)
        // =============================================
        this.ssaoPass = new SSAOPass(this.scene, this.camera, width, height);
        this.ssaoPass.kernelRadius = 16;
        this.ssaoPass.minDistance = 0.005;
        this.ssaoPass.maxDistance = 0.1;
        this.composer.addPass(this.ssaoPass);
        
        // =============================================
        // Bloom (soft glow for lights)
        // =============================================
        this.bloomPass = new UnrealBloomPass(
            new THREE.Vector2(width, height),
            0.4,  // strength
            0.4,  // radius
            0.85   // threshold
        );
        this.composer.addPass(this.bloomPass);
        
        // =============================================
        // FXAA (Anti-aliasing)
        // =============================================
        this.fxaaPass = new ShaderPass(FXAAShader);
        this.fxaaPass.uniforms['resolution'].value.set(
            1 / width,
            1 / height
        );
        this.composer.addPass(this.fxaaPass);
        
        // =============================================
        // Output/Tone Mapping
        // =============================================
        const outputPass = new OutputPass();
        this.composer.addPass(outputPass);
    }
    
    /**
     * Render with post-processing
     */
    render() {
        if (this.composer) {
            this.composer.render();
        }
    }
    
    /**
     * Resize handler
     */
    resize(width: number, height: number) {
        if (this.composer) {
            this.composer.setSize(width, height);
        }
        if (this.ssaoPass) {
            this.ssaoPass.setSize(width, height);
        }
        if (this.fxaaPass) {
            this.fxaaPass.uniforms['resolution'].value.set(1/width, 1/height);
        }
    }
    
    /**
     * Toggle effects on/off
     */
    toggleSSAO(enabled: boolean) {
        if (this.ssaoPass) {
            this.ssaoPass.enabled = enabled;
        }
    }
    
    toggleBloom(enabled: boolean) {
        if (this.bloomPass) {
            this.bloomPass.enabled = enabled;
        }
    }
}

/**
 * Advanced Lighting Setup
 * Creates realistic studio-like lighting
 */
export class AdvancedLighting {
    private lights: THREE.Light[] = [];
    private scene: THREE.Scene;
    
    constructor(scene: THREE.Scene) {
        this.scene = scene;
        this.setup();
    }
    
    private setup() {
        // =============================================
        // Hemisphere Light (Sky/Ground ambient)
        // =============================================
        const hemiLight = new THREE.HemisphereLight(
            0xddeeff,  // sky color
            0x889966,  // ground color
            0.6        // intensity
        );
        hemiLight.position.set(0, 20, 0);
        this.lights.push(hemiLight);
        this.scene.add(hemiLight);
        
        // =============================================
        // Main Directional Light (Sun)
        // =============================================
        const sunLight = new THREE.DirectionalLight(0xffffff, 1.2);
        sunLight.position.set(50, 50, 30);
        sunLight.castShadow = true;
        
        // Shadow configuration
        sunLight.shadow.mapSize.width = 2048;
        sunLight.shadow.mapSize.height = 2048;
        sunLight.shadow.camera.near = 0.5;
        sunLight.shadow.camera.far = 500;
        sunLight.shadow.camera.left = -50;
        sunLight.shadow.camera.right = 50;
        sunLight.shadow.camera.top = 50;
        sunLight.shadow.camera.bottom = -50;
        sunLight.shadow.bias = -0.0001;
        
        this.lights.push(sunLight);
        this.scene.add(sunLight);
        
        // =============================================
        // Fill Light
        // =============================================
        const fillLight = new THREE.DirectionalLight(0xfff5ee, 0.4);
        fillLight.position.set(-30, 20, -20);
        this.lights.push(fillLight);
        this.scene.add(fillLight);
        
        // =============================================
        // Rim Light (for edges)
        // =============================================
        const rimLight = new THREE.DirectionalLight(0xe8f0ff, 0.3);
        rimLight.position.set(0, 30, -50);
        this.lights.push(rimLight);
        this.scene.add(rimLight);
        
        // =============================================
        // Point Lights for warm accents
        // =============================================
        const accentLight = new THREE.PointLight(0xffaa66, 0.3, 20);
        accentLight.position.set(5, 3, 5);
        this.lights.push(accentLight);
        this.scene.add(accentLight);
    }
    
    /**
     * Get main shadow light for target
     */
    getShadowLight(): THREE.DirectionalLight | undefined {
        return this.lights.find(l => l.type === 'DirectionalLight') as THREE.DirectionalLight;
    }
    
    /**
     * Clean up
     */
    dispose() {
        this.lights.forEach(light => {
            this.scene.remove(light);
            if ((light as any).dispose) {
                (light as any).dispose();
            }
        });
        this.lights = [];
    }
}

/**
 * Shadow Ground Plane
 * Receives shadows from building
 */
export class ShadowGround {
    private mesh: THREE.Mesh;
    
    constructor(scene: THREE.Scene) {
        // Create ground with shadow-receiving material
        const groundGeometry = new THREE.PlaneGeometry(100, 100);
        const groundMaterial = new THREE.ShadowMaterial({
            opacity: 0.3
        });
        
        this.mesh = new THREE.Mesh(groundGeometry, groundMaterial);
        this.mesh.rotation.x = -Math.PI / 2;
        this.mesh.position.y = -0.01;
        this.mesh.receiveShadow = true;
        
        scene.add(this.mesh);
        
        // Also add visible ground for aesthetics
        const visGroundMat = new THREE.MeshStandardMaterial({
            color: 0x809070,
            roughness: 0.9,
            metalness: 0
        });
        const visGround = new THREE.Mesh(groundGeometry, visGroundMat);
        visGround.rotation.x = -Math.PI / 2;
        visGround.position.y = -0.02;
        visGround.receiveShadow = true;
        
        scene.add(visGround);
    }
    
    dispose() {
        this.mesh.geometry.dispose();
        (this.mesh.material as THREE.Material).dispose();
    }
}

/**
 * Environment Map for reflections
 * Creates studio-like HDRI environment
 */
export function createEnvironmentMap(renderer: THREE.WebGLRenderer): THREE.Texture {
    const pmremGenerator = new THREE.PMREMGenerator(renderer);
    pmremGenerator.compileEquirectangularShader();
    
    // Create simple gradient environment
    const envScene = new THREE.Scene();
    
    // Create a large sphere with gradient
    const envGeom = new THREE.SphereGeometry(500, 64, 64);
    const envMat = new THREE.MeshBasicMaterial({
        side: THREE.BackSide,
        vertexColors: true
    });
    
    // Add vertex colors for gradient
    const colors = [];
    const positions = envGeom.attributes.position;
    for (let i = 0; i < positions.count; i++) {
        const y = positions.getY(i);
        const normalizedY = (y + 500) / 1000;
        
        // Gradient from bottom (ground color) to top (sky color)
        const color = new THREE.Color();
        if (normalizedY > 0.6) {
            // Sky - light blue
            color.setRGB(0.5 + normalizedY * 0.5, 0.7 + normalizedY * 0.3, 0.9);
        } else if (normalizedY > 0.3) {
            // Horizon - warm white
            color.setRGB(0.9, 0.85, 0.8);
        } else {
            // Ground - darker
            color.setRGB(0.3, 0.3, 0.35);
        }
        colors.push(color.r, color.g, color.b);
    }
    envGeom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    
    const envSphere = new THREE.Mesh(envGeom, envMat);
    envScene.add(envSphere);
    
    // Generate environment map
    const envMap = pmremGenerator.fromScene(envScene, 0, 0.1, 1000).texture;
    pmremGenerator.dispose();
    
    return envMap;
}