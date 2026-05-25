-- =====================================================
-- AI ARCHITECT — PRODUCTION DATABASE SCHEMA
-- =====================================================
-- Supabase PostgreSQL + pgvector for semantic search

-- ---- Enable Extensions ----
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =====================================================
-- 1. AUTHENTICATION & USERS
-- =====================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- =====================================================
-- 2. PROJECTS & SCENES
-- =====================================================

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_public BOOLEAN DEFAULT FALSE,
    thumbnail_url TEXT,
    metadata JSONB DEFAULT '{}'::JSONB
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- =====================================================
-- 3. SCENES (CANONICAL SCENE GRAPH)
-- =====================================================

CREATE TABLE scenes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'draft', -- draft, rendering, completed, failed
    
    -- Canonical Scene Graph (JSON)
    scene_graph JSONB NOT NULL DEFAULT '{
        "rooms": [],
        "walls": [],
        "windows": [],
        "doors": [],
        "stairs": [],
        "furniture": [],
        "materials": [],
        "lighting": [],
        "navigation": []
    }'::JSONB,
    
    -- Rendering Assets
    asset_urls JSONB DEFAULT '{
        "glb": null,
        "splat": null,
        "thumbnail": null,
        "preview_frames": []
    }'::JSONB,
    
    -- Generation Metadata
    generation_history JSONB DEFAULT '[]'::JSONB,
    generation_prompt TEXT,
    generation_parameters JSONB DEFAULT '{}'::JSONB,
    
    -- Semantic Embeddings
    semantic_embedding vector(1536),
    room_tags TEXT[],
    style_tags TEXT[],
    output_mode VARCHAR(50) DEFAULT 'fast_preview',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    render_started_at TIMESTAMP,
    render_completed_at TIMESTAMP
);

CREATE INDEX idx_scenes_project_id ON scenes(project_id);
CREATE INDEX idx_scenes_user_id ON scenes(user_id);
CREATE INDEX idx_scenes_status ON scenes(status);
CREATE INDEX idx_scenes_semantic ON scenes USING ivfflat (semantic_embedding vector_cosine_ops);

-- =====================================================
-- 4. SCENE VERSIONS (Immutable History)
-- =====================================================

CREATE TABLE scene_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    scene_graph JSONB NOT NULL,
    change_description TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_scene_versions_scene_id ON scene_versions(scene_id);
CREATE UNIQUE INDEX idx_scene_versions_unique ON scene_versions(scene_id, version_number);

-- =====================================================
-- 5. ROOMS (Extracted from Scene Graph)
-- =====================================================

CREATE TABLE rooms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    room_type VARCHAR(100) NOT NULL, -- bedroom, kitchen, bathroom, living, etc.
    name VARCHAR(255),
    position_x FLOAT,
    position_y FLOAT,
    position_z FLOAT,
    width FLOAT,
    depth FLOAT,
    height FLOAT,
    area FLOAT,
    floor_number INTEGER,
    color_rgb VARCHAR(7), -- #RRGGBB
    material_id UUID REFERENCES materials(id),
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rooms_scene_id ON rooms(scene_id);
CREATE INDEX idx_rooms_room_type ON rooms(room_type);

-- =====================================================
-- 6. MATERIALS & TEXTURES
-- =====================================================

CREATE TABLE materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    material_type VARCHAR(100), -- wood, concrete, glass, fabric, etc.
    color_rgb VARCHAR(7),
    roughness FLOAT DEFAULT 0.5, -- 0.0 to 1.0
    metallic FLOAT DEFAULT 0.0,   -- 0.0 to 1.0
    texture_url TEXT,
    albedo_url TEXT,
    normal_url TEXT,
    roughness_url TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    is_default BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_materials_material_type ON materials(material_type);
CREATE INDEX idx_materials_is_default ON materials(is_default);

-- =====================================================
-- 7. ASSETS & FURNITURE
-- =====================================================

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(100), -- furniture, fixture, decoration, etc.
    category VARCHAR(100), -- sofa, chair, bed, table, lamp, etc.
    model_url TEXT NOT NULL, -- glTF/GLB URL
    thumbnail_url TEXT,
    bounding_box JSONB, -- {min: {x,y,z}, max: {x,y,z}}
    scale FLOAT DEFAULT 1.0,
    tags TEXT[],
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    is_premium BOOLEAN DEFAULT FALSE,
    is_default BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::JSONB
);

CREATE INDEX idx_assets_asset_type ON assets(asset_type);
CREATE INDEX idx_assets_category ON assets(category);
CREATE INDEX idx_assets_is_default ON assets(is_default);

-- =====================================================
-- 8. AGENT EXECUTION LOGS
-- =====================================================

CREATE TABLE agent_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scene_id UUID REFERENCES scenes(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL, -- orchestrator, planner, geometry, etc.
    agent_role VARCHAR(50), -- primary or evaluator (bull/bear/skeptic)
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    input_prompt TEXT,
    output_result JSONB,
    error_message TEXT,
    token_usage JSONB DEFAULT '{"input": 0, "output": 0}'::JSONB,
    execution_time_ms INTEGER,
    model_used VARCHAR(100),
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX idx_agent_executions_scene_id ON agent_executions(scene_id);
CREATE INDEX idx_agent_executions_user_id ON agent_executions(user_id);
CREATE INDEX idx_agent_executions_agent_name ON agent_executions(agent_name);
CREATE INDEX idx_agent_executions_status ON agent_executions(status);
CREATE INDEX idx_agent_executions_created_at ON agent_executions(created_at DESC);

-- =====================================================
-- 9. RENDER JOBS
-- =====================================================

CREATE TABLE render_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'queued', -- queued, rendering, completed, failed
    render_type VARCHAR(50), -- preview, glb, splat, viewport
    output_url TEXT,
    error_message TEXT,
    progress_percent INTEGER DEFAULT 0,
    estimated_time_sec INTEGER,
    actual_time_sec INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- =====================================================
-- 10. ARTIFACTS (Progressive Artifact Outputs)
-- =====================================================

CREATE TABLE artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scene_id UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    stage VARCHAR(50) NOT NULL, -- floorplan, preview, furnished, cinematic, walkthrough
    artifact_type VARCHAR(20) NOT NULL, -- svg, png, gltf, glb, mp4, ifc, obj
    status VARCHAR(20) DEFAULT 'queued', -- queued, processing, completed, failed
    url TEXT,
    preview_url TEXT,
    error_message TEXT,
    metadata_json JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_artifacts_scene_id ON artifacts(scene_id);
CREATE INDEX idx_artifacts_stage ON artifacts(stage);
CREATE INDEX idx_artifacts_status ON artifacts(status);

-- =====================================================
-- 12. API KEYS & INTEGRATIONS
-- =====================================================

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_name VARCHAR(255) NOT NULL,
    key_value VARCHAR(500) NOT NULL, -- encrypted in practice
    key_type VARCHAR(100), -- openrouter, huggingface, replicate, etc.
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);

-- =====================================================
-- 13. WEBHOOKS & EVENTS
-- =====================================================

CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    scene_id UUID REFERENCES scenes(id) ON DELETE SET NULL,
    event_type VARCHAR(100), -- scene.created, render.completed, agent.error, etc.
    event_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_user_id ON events(user_id);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_created_at ON events(created_at DESC);

-- =====================================================
-- 14. AUDIT LOG
-- =====================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100), -- create, update, delete, render, etc.
    resource_type VARCHAR(100), -- scene, project, user, etc.
    resource_id UUID,
    changes JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- =====================================================
-- Row Level Security (RLS) Policies
-- =====================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenes ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_executions ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY users_policy ON users
    FOR SELECT USING (id = auth.uid());

-- Users can only see their own projects
CREATE POLICY projects_policy ON projects
    FOR SELECT USING (user_id = auth.uid() OR is_public = true);

-- Users can only see their own scenes
CREATE POLICY scenes_policy ON scenes
    FOR SELECT USING (user_id = auth.uid());

-- Users can only see their own agent executions
CREATE POLICY agent_executions_policy ON agent_executions
    FOR SELECT USING (user_id = auth.uid());
