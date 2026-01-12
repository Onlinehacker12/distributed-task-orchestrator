import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_requires_key(client):
    r = client.get("/v1/health")
    assert r.status_code in (401, 422)


def test_metrics_requires_key(client):
    r = client.get("/v1/metrics")
    assert r.status_code in (401, 422)