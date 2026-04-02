"""
Test API endpoints
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_root(client: TestClient):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_check(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"healthy", "degraded"}
    assert "database" in data


def test_diagnose_no_file(client: TestClient):
    """Test diagnose endpoint without file"""
    response = client.post("/api/diagnose")
    assert response.status_code == 422  # Validation error


def test_diagnose_invalid_file(client: TestClient):
    """Test diagnose endpoint with invalid file type"""
    # Create a text file
    files = {"file": ("test.txt", b"test content", "text/plain")}
    response = client.post("/api/diagnose", files=files)
    assert response.status_code == 400


# TODO: Add test with actual image file
# def test_diagnose_valid_image():
#     """Test diagnose with valid image"""
#     with open("tests/fixtures/sample_ecg.png", "rb") as f:
#         files = {"file": ("test.png", f, "image/png")}
#         response = client.post("/api/diagnose", files=files)
#         assert response.status_code == 200
#         data = response.json()
#         assert "prediction" in data
#         assert "confidence" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
