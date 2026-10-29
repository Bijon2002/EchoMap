"""
test_server.py - Tests for FastAPI server endpoints in EchoMap
"""

import pytest
from fastapi.testclient import TestClient
import server


@pytest.fixture
def client():
    return TestClient(server.app)


def test_index_serves_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "EchoMap" in res.text
    assert "2D Spatial Radar" in res.text


def test_system_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert "gemini_model" in data
    assert data["app_title"] == "EchoMap: Your World, Remembered"


def test_sample_memory_and_query(client):
    # Load sample desk memory
    res = client.post("/api/demo/sample")
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Check latest scan
    res = client.get("/api/scans/latest")
    assert res.status_code == 200
    latest = res.json()
    assert latest["has_scan"] is True
    assert len(latest["objects"]) == 7

    # Check natural language query
    res = client.post("/api/query", json={"query": "Where are my keys?"})
    assert res.status_code == 200
    answer = res.json()["answer"]
    assert "keys" in answer.lower()


def test_movement_diff(client):
    # Simulate moved keys
    res = client.post("/api/demo/simulate-diff")
    assert res.status_code == 200

    # Retrieve diff
    res = client.get("/api/diff")
    assert res.status_code == 200
    diff_data = res.json()
    assert diff_data["has_diff"] is True
    assert len(diff_data["diffs"]) > 0


def test_corrections_lifecycle(client):
    res = client.post(
        "/api/corrections",
        json={
            "object_name": "keys",
            "relation_type": "beside",
            "reference_object": "laptop",
            "note": "On the mousepad",
        },
    )
    assert res.status_code == 200
    corr_id = res.json()["id"]

    res = client.get("/api/corrections")
    assert res.status_code == 200
    corrs = res.json()["corrections"]
    assert any(c["id"] == corr_id for c in corrs)

    # Delete correction
    res = client.delete(f"/api/corrections/{corr_id}")
    assert res.status_code == 200


def test_tts_generation(client):
    res = client.post("/api/tts", json={"text": "Keys are on your desk.", "tld": "co.uk"})
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mpeg"
    assert len(res.content) > 1000

