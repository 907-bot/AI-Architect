"""
SQLAlchemy ORM Models for AI Architect
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    ForeignKey, Text, JSON, ARRAY, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()

# =====================================================
# 1. USERS
# =====================================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    avatar_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    scenes = relationship("Scene", back_populates="user", cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="user", cascade="all, delete-orphan")
    render_jobs = relationship("RenderJob", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")


# =====================================================
# 2. PROJECTS
# =====================================================

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_public = Column(Boolean, default=False)
    thumbnail_url = Column(Text)
    meta_data = Column("metadata", JSONB, default={})
    
    # Relationships
    user = relationship("User", back_populates="projects")
    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan")


# =====================================================
# 3. SCENES (Canonical Scene Graph)
# =====================================================

class Scene(Base):
    __tablename__ = "scenes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(Integer, default=1)
    status = Column(String(50), default="draft", index=True)  # draft, rendering, completed, failed
    
    # Canonical Scene Graph
    scene_graph = Column(JSONB, nullable=False, default={
        "rooms": [],
        "walls": [],
        "windows": [],
        "doors": [],
        "stairs": [],
        "furniture": [],
        "materials": [],
        "lighting": [],
        "navigation": []
    })
    
    # Rendering Assets
    asset_urls = Column(JSONB, default={
        "glb": None,
        "splat": None,
        "thumbnail": None,
        "preview_frames": []
    })
    
    # Generation Metadata
    generation_history = Column(JSONB, default=[])
    generation_prompt = Column(Text)
    generation_parameters = Column(JSONB, default={})
    
    # Semantic embeddings (vector)
    semantic_embedding = Column(JSON)  # Stored as JSON, indexed separately
    room_tags = Column(ARRAY(String))
    style_tags = Column(ARRAY(String))
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    render_started_at = Column(DateTime)
    render_completed_at = Column(DateTime)
    
    # Relationships
    project = relationship("Project", back_populates="scenes")
    user = relationship("User", back_populates="scenes")
    rooms = relationship("Room", back_populates="scene", cascade="all, delete-orphan")
    versions = relationship("SceneVersion", back_populates="scene", cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="scene", cascade="all, delete-orphan")
    render_jobs = relationship("RenderJob", back_populates="scene", cascade="all, delete-orphan")


# =====================================================
# 4. SCENE VERSIONS
# =====================================================

class SceneVersion(Base):
    __tablename__ = "scene_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id = Column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    scene_graph = Column(JSONB, nullable=False)
    change_description = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('scene_id', 'version_number', name='uq_scene_version'),
    )
    
    # Relationships
    scene = relationship("Scene", back_populates="versions")
    creator = relationship("User")


# =====================================================
# 5. ROOMS
# =====================================================

class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id = Column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    room_type = Column(String(100), nullable=False, index=True)  # bedroom, kitchen, etc.
    name = Column(String(255))
    position_x = Column(Float)
    position_y = Column(Float)
    position_z = Column(Float)
    width = Column(Float)
    depth = Column(Float)
    height = Column(Float)
    area = Column(Float)
    floor_number = Column(Integer)
    color_rgb = Column(String(7))  # #RRGGBB
    material_id = Column(UUID(as_uuid=True), ForeignKey("materials.id"))
    meta_data = Column("metadata", JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    scene = relationship("Scene", back_populates="rooms")
    material = relationship("Material")


# =====================================================
# 6. MATERIALS
# =====================================================

class Material(Base):
    __tablename__ = "materials"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    name = Column(String(255), nullable=False)
    material_type = Column(String(100), index=True)
    color_rgb = Column(String(7))
    roughness = Column(Float, default=0.5)
    metallic = Column(Float, default=0.0)
    texture_url = Column(Text)
    albedo_url = Column(Text)
    normal_url = Column(Text)
    roughness_url = Column(Text)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_default = Column(Boolean, default=False, index=True)


# =====================================================
# 7. ASSETS
# =====================================================

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    name = Column(String(255), nullable=False)
    asset_type = Column(String(100), index=True)
    category = Column(String(100), index=True)
    model_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text)
    bounding_box = Column(JSONB)
    scale = Column(Float, default=1.0)
    tags = Column(ARRAY(String))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_premium = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False, index=True)
    meta_data = Column("metadata", JSONB, default={})


# =====================================================
# 8. AGENT EXECUTIONS
# =====================================================

class AgentExecution(Base):
    __tablename__ = "agent_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id = Column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="SET NULL"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    agent_role = Column(String(50))  # primary or evaluator
    status = Column(String(50), default="pending", index=True)
    input_prompt = Column(Text)
    output_result = Column(JSONB)
    error_message = Column(Text)
    token_usage = Column(JSONB, default={"input": 0, "output": 0})
    execution_time_ms = Column(Integer)
    model_used = Column(String(100))
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    scene = relationship("Scene", back_populates="agent_executions")
    project = relationship("Project")
    user = relationship("User", back_populates="agent_executions")


# =====================================================
# 9. RENDER JOBS
# =====================================================

class RenderJob(Base):
    __tablename__ = "render_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scene_id = Column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="queued", index=True)
    render_type = Column(String(50))
    output_url = Column(Text)
    error_message = Column(Text)
    progress_percent = Column(Integer, default=0)
    estimated_time_sec = Column(Integer)
    actual_time_sec = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    scene = relationship("Scene", back_populates="render_jobs")
    user = relationship("User", back_populates="render_jobs")


# =====================================================
# 10. API KEYS
# =====================================================

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_name = Column(String(255), nullable=False)
    key_value = Column(String(500), nullable=False)
    key_type = Column(String(100))
    is_active = Column(Boolean, default=True, index=True)
    last_used_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")


# =====================================================
# 11. EVENTS
# =====================================================

class Event(Base):
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    scene_id = Column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="SET NULL"))
    event_type = Column(String(100), index=True)
    event_data = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# =====================================================
# 12. AUDIT LOG
# =====================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(100))
    resource_type = Column(String(100), index=True)
    resource_id = Column(UUID(as_uuid=True))
    changes = Column(JSONB)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
