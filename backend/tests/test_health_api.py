from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_api_is_registered():
    routes = {route.path for route in app.routes}
    assert "/api/health/jobs" in routes
