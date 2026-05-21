import pytest
from fastapi.testclient import TestClient
from backend.main import app


def test_root():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data


def test_health_status():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    d = resp.json()
    assert "status" in d
