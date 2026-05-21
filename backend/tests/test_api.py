"""
Test suite for AI Architect backend
Tests authentication, API routes, agents, and database operations
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime
import uuid

from backend.main import app
from backend.database.models import Base, User, Project, Scene
from backend.database.client import db_client
from backend.auth.jwt import hash_password, get_jwt_handler


# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def test_db():
    """Create in-memory SQLite test database"""
    # Use SQLite for testing (faster, no external dependencies)
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    yield TestingSessionLocal
    
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """Create test client"""
    
    def override_get_db():
        db = test_db()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[db_client.get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def test_user(test_db):
    """Create test user"""
    db = test_db()
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        password_hash=hash_password("password123"),
        full_name="Test User",
        is_active=True
    )
    db.add(user)
        db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Create JWT token for test user"""
    jwt_handler = get_jwt_handler("test-secret")
    token, _ = jwt_handler.create_access_token(
        user_id=str(test_user.id),
        email=test_user.email,
        username=test_user.username
    )
    return token


# =====================================================
# AUTH TESTS
# =====================================================

def test_signup(client):
    """Test user registration"""
    response = client.post("/api/auth/signup", json={
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "securepass123",
        "full_name": "New User"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"


def test_signup_duplicate_email(client, test_user):
    """Test signup with existing email"""
    response = client.post("/api/auth/signup", json={
        "email": test_user.email,
        "username": "anotheruser",
        "password": "pass123"
    })
    
    assert response.status_code == 409


def test_login(client, test_user):
    """Test user login"""
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    """Test login with wrong password"""
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401


def test_get_current_user(client, auth_token):
    """Test get current user"""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


def test_get_current_user_no_token(client):
    """Test get current user without token"""
    response = client.get("/api/auth/me")
    
    assert response.status_code == 401


# =====================================================
# PROJECTS TESTS
# =====================================================

def test_create_project(client, auth_token):
    """Test project creation"""
    response = client.post(
        "/api/projects",
        json={
            "name": "Test Project",
            "description": "A test project",
            "is_public": False
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Project"


def test_list_projects(client, auth_token):
    """Test list projects"""
    # Create a project first
    client.post(
        "/api/projects",
        json={"name": "Project 1"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    response = client.get(
        "/api/projects",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Project 1"


def test_delete_project(client, auth_token, test_db):
    """Test project deletion"""
    db = test_db()
    
    # Create project
    response = client.post(
        "/api/projects",
        json={"name": "Project to Delete"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    project_id = response.json()["id"]
    
    # Delete project
    response = client.delete(
        f"/api/projects/{project_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 204


# =====================================================
# SCENES TESTS
# =====================================================

def test_create_scene(client, auth_token, test_db):
    """Test scene creation"""
    db = test_db()
    
    # Create project first
    project_response = client.post(
        "/api/projects",
        json={"name": "Test Project"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    project_id = project_response.json()["id"]
    
    # Create scene
    response = client.post(
        "/api/scenes",
        json={
            "project_id": project_id,
            "name": "Test Scene",
            "description": "A test scene",
            "generation_prompt": "Modern 3-bedroom house"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Scene"
    assert data["status"] == "draft"


def test_get_scene(client, auth_token, test_db):
    """Test get scene details"""
    db = test_db()
    
    # Create scene
    project_response = client.post(
        "/api/projects",
        json={"name": "Test Project"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    project_id = project_response.json()["id"]
    
    scene_response = client.post(
        "/api/scenes",
        json={
            "project_id": project_id,
            "name": "Test Scene"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    scene_id = scene_response.json()["id"]
    
    # Get scene
    response = client.get(
        f"/api/scenes/{scene_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Scene"
    assert "scene_graph" in data


def test_update_scene(client, auth_token, test_db):
    """Test scene update"""
    db = test_db()
    
    # Create scene
    project_response = client.post(
        "/api/projects",
        json={"name": "Test Project"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    project_id = project_response.json()["id"]
    
    scene_response = client.post(
        "/api/scenes",
        json={
            "project_id": project_id,
            "name": "Original Name"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    scene_id = scene_response.json()["id"]
    
    # Update scene
    response = client.put(
        f"/api/scenes/{scene_id}",
        json={"name": "Updated Name"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["version"] > 1


# =====================================================
# AGENTS TESTS
# =====================================================

def test_generate_scene_request(client, auth_token, test_db):
    """Test scene generation request"""
    db = test_db()
    
    # Create scene
    project_response = client.post(
        "/api/projects",
        json={"name": "Test Project"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    project_id = project_response.json()["id"]
    
    scene_response = client.post(
        "/api/scenes",
        json={
            "project_id": project_id,
            "name": "Test Scene"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    scene_id = scene_response.json()["id"]
    
    # Generate scene
    response = client.post(
        "/api/agents/generate",
        json={
            "scene_id": scene_id,
            "prompt": "Modern minimalist 3-bedroom house",
            "style": "modern"
        },
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"


# =====================================================
# HEALTH TESTS
# =====================================================

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]


def test_api_status(client):
    """Test API status endpoint"""
    response = client.get("/status")
    
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "AI Architect"


# =====================================================
# SCENE GRAPH VALIDATION TESTS
# =====================================================

def test_scene_graph_validation():
    """Test scene graph schema validation"""
    from backend.models.scene_graph import SceneGraph, RoomSpec, Vector3, SceneValidator
    
    # Create valid scene graph
    scene = SceneGraph(
        rooms=[
            RoomSpec(
                id="room_1",
                room_type="bedroom",
                name="Master Bedroom",
                floor_number=1,
                position=Vector3(x=0, y=0, z=0),
                width=15,
                depth=15,
                height=9,
                material_id="mat_1",
                walls=[],
                windows=[],
                doors=[],
                furniture=[],
                lights=[]
            )
        ],
        stairs=[],
        materials=[],
        lights=[],
        navigation={"navigation_meshes": [], "walkthrough_points": [], "drone_path_nodes": []}
    )
    
    # Validate
    is_valid, errors = SceneValidator.validate_scene_graph(scene)
    assert is_valid
    assert len(errors) == 0


def test_scene_graph_invalid_dimensions():
    """Test scene graph validation with invalid dimensions"""
    from backend.models.scene_graph import SceneGraph, RoomSpec, Vector3, SceneValidator
    
    # Create scene with tiny room (invalid)
    scene = SceneGraph(
        rooms=[
            RoomSpec(
                id="room_1",
                room_type="bedroom",
                name="Tiny Room",
                floor_number=1,
                position=Vector3(x=0, y=0, z=0),
                width=2,  # Too small!
                depth=2,  # Too small!
                height=5,  # Too small!
                material_id="mat_1",
                walls=[],
                windows=[],
                doors=[],
                furniture=[],
                lights=[]
            )
        ],
        stairs=[],
        materials=[],
        lights=[],
        navigation={"navigation_meshes": [], "walkthrough_points": [], "drone_path_nodes": []}
    )
    
    is_valid, errors = SceneValidator.validate_scene_graph(scene)
    assert not is_valid
    assert len(errors) > 0


# =====================================================
# RUN TESTS
# =====================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
