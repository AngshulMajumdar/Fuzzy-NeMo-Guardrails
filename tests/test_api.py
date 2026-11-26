from fastapi.testclient import TestClient
from fuzzy_nemo.api import app

client = TestClient(app)


def test_health_and_config():
    assert client.get("/health").json()["status"] == "ok"
    assert "input" in client.get("/config").json()["phases"]


def test_safe():
    resp = client.post("/evaluate", json={"phase":"input", "scores": {"injection_risk":.05,"toxicity_risk":.05}})
    assert resp.status_code == 200 and resp.json()["decision"] == "allow"


def test_missing_score_is_review():
    resp = client.post("/evaluate", json={"phase":"input", "scores": {"injection_risk":.05}})
    assert resp.status_code == 200 and resp.json()["decision"] == "review"


def test_unknown_feature_rejected():
    resp = client.post("/evaluate", json={"phase":"input", "scores": {"fake":0.1}})
    assert resp.status_code == 422
