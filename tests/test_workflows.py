"""Workflow triggering and the n8n callback route."""


def test_trigger_without_n8n_configured_records_a_simulated_run(client, tokens, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "N8N_WEBHOOK_URL", None)

    resp = client.post(
        "/api/v1/workflows/trigger",
        headers=tokens["analyst"],
        json={"workflow_name": "document-intake", "payload": {}},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "success"
    assert body["result"]["simulated"] is True
    assert body["duration_ms"] is not None


def test_viewer_cannot_trigger_a_workflow(client, tokens):
    resp = client.post(
        "/api/v1/workflows/trigger",
        headers=tokens["viewer"],
        json={"workflow_name": "x", "payload": {}},
    )
    assert resp.status_code == 403


def test_callback_requires_no_authentication(client):
    """n8n posts here directly; it holds no platform user token."""
    resp = client.post(
        "/api/v1/workflows/callback",
        json={
            "workflow_name": "enterprise-email-to-ticket",
            "payload": {"result": {"ticket": "TKT-2026-1"}, "duration_ms": 800},
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["trigger_source"] == "n8n"
    assert body["status"] == "success"
    assert body["result"] == {"ticket": "TKT-2026-1"}


def test_runs_can_be_listed_and_filtered_by_status(client, tokens):
    client.post(
        "/api/v1/workflows/trigger",
        headers=tokens["analyst"],
        json={"workflow_name": "a", "payload": {}},
    )
    client.post(
        "/api/v1/workflows/callback",
        json={"workflow_name": "b", "payload": {}},
    )

    resp = client.get(
        "/api/v1/workflows/runs", headers=tokens["viewer"], params={"status": "success"}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_fetching_a_missing_run_is_404(client, tokens):
    resp = client.get("/api/v1/workflows/runs/999", headers=tokens["viewer"])
    assert resp.status_code == 404
