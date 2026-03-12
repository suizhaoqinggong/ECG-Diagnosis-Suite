"""
Test API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_diagnose_no_file():
    """Test diagnose endpoint without file"""
    response = client.post("/api/diagnose")
    assert response.status_code == 422  # Validation error


def test_diagnose_invalid_file():
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
