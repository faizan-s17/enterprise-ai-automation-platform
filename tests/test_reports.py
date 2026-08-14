"""Metrics collection and report generation."""


def test_live_metrics_has_the_expected_shape(client, tokens):
    resp = client.get(
        "/api/v1/reports/metrics", headers=tokens["viewer"], params={"days": 30}
    )
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "documents_total", "tickets_total", "approvals_total",
        "workflow_runs", "workflow_success_rate",
    ):
        assert key in body


def test_generating_a_report_reflects_created_tickets(client, tokens):
    client.post(
        "/api/v1/tickets",
        headers=tokens["analyst"],
        json={"subject": "x", "priority": "urgent", "category": "technical"},
    )

    resp = client.post(
        "/api/v1/reports/generate",
        headers=tokens["manager"],
        json={"kind": "operations", "days": 30},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["metrics"]["tickets_total"] == 1
    assert body["metrics"]["tickets_urgent"] == 1
    assert body["narrative"]


def test_report_narrative_has_no_markdown_when_using_the_local_fallback(client, tokens):
    """The local fallback is deterministic prose; asserting this pins that
    behaviour so a future change to the template is a visible diff, not a
    silent regression."""
    resp = client.post(
        "/api/v1/reports/generate",
        headers=tokens["manager"],
        json={"kind": "operations", "days": 30},
    )
    narrative = resp.json()["narrative"]
    assert "*" not in narrative
    assert "#" not in narrative


def test_reports_can_be_listed_and_fetched_by_id(client, tokens):
    created = client.post(
        "/api/v1/reports/generate",
        headers=tokens["manager"],
        json={"kind": "operations", "days": 7},
    ).json()

    listing = client.get("/api/v1/reports", headers=tokens["viewer"])
    assert listing.status_code == 200
    assert any(r["id"] == created["id"] for r in listing.json())

    fetched = client.get(f"/api/v1/reports/{created['id']}", headers=tokens["viewer"])
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


def test_fetching_a_missing_report_is_404(client, tokens):
    resp = client.get("/api/v1/reports/999", headers=tokens["viewer"])
    assert resp.status_code == 404
