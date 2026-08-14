"""Ticket creation, AI triage (rule-based fallback), and status transitions."""


def test_create_ticket_with_explicit_priority_skips_triage(client, tokens):
    resp = client.post(
        "/api/v1/tickets",
        headers=tokens["analyst"],
        json={"subject": "Routine check-in", "priority": "low", "category": "general"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["priority"] == "low"
    assert body["ai_classified"] is False
    assert body["reference"].startswith("TKT-")


def test_create_ticket_without_priority_gets_auto_triaged(client, tokens):
    resp = client.post(
        "/api/v1/tickets",
        headers=tokens["analyst"],
        json={
            "subject": "URGENT: production outage",
            "description": "The API is down and customers cannot log in.",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["priority"] == "urgent"
    assert body["category"] == "technical"
    assert body["ai_reasoning"]


def test_viewer_cannot_create_tickets(client, tokens):
    resp = client.post(
        "/api/v1/tickets", headers=tokens["viewer"], json={"subject": "x"}
    )
    assert resp.status_code == 403


def test_inbound_email_requires_no_authentication(client):
    """An email automation posting here has no user token to present."""
    resp = client.post(
        "/api/v1/tickets/inbound-email",
        json={
            "from_email": "vendor@example.com",
            "subject": "Invoice payment overdue",
            "body": "A late fee now applies.",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source"] == "email"
    assert body["requester_email"] == "vendor@example.com"
    assert body["priority"] == "urgent"
    assert body["category"] == "billing"


def test_inbound_email_strips_the_quoted_reply_before_triage(client):
    body_with_thread = (
        "Please look into this.\n\n"
        "On Mon, Aug 10, 2026, someone wrote:\n"
        "> irrelevant quoted urgent outage text that should not be seen"
    )
    resp = client.post(
        "/api/v1/tickets/inbound-email",
        json={
            "from_email": "person@example.com",
            "subject": "A question",
            "body": body_with_thread,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["description"] == "Please look into this."


def test_listing_can_filter_by_status_and_priority(client, tokens):
    client.post(
        "/api/v1/tickets",
        headers=tokens["analyst"],
        json={"subject": "A", "priority": "high", "category": "technical"},
    )
    client.post(
        "/api/v1/tickets",
        headers=tokens["analyst"],
        json={"subject": "B", "priority": "low", "category": "general"},
    )

    resp = client.get(
        "/api/v1/tickets", headers=tokens["analyst"], params={"priority": "high"}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["subject"] == "A"


def test_updating_status_to_resolved_stamps_resolved_at(client, tokens):
    ticket = client.post(
        "/api/v1/tickets",
        headers=tokens["analyst"],
        json={"subject": "Fix it", "priority": "medium", "category": "general"},
    ).json()
    assert ticket["resolved_at"] is None

    resp = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        headers=tokens["analyst"],
        json={"status": "resolved"},
    )
    assert resp.status_code == 200
    assert resp.json()["resolved_at"] is not None


def test_reopening_a_resolved_ticket_clears_resolved_at(client, tokens):
    ticket = client.post(
        "/api/v1/tickets",
        headers=tokens["analyst"],
        json={"subject": "Fix it", "priority": "medium", "category": "general"},
    ).json()
    client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        headers=tokens["analyst"],
        json={"status": "resolved"},
    )

    resp = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        headers=tokens["analyst"],
        json={"status": "open"},
    )
    assert resp.status_code == 200
    assert resp.json()["resolved_at"] is None


def test_assigning_to_a_nonexistent_user_is_rejected(client, tokens):
    ticket = client.post(
        "/api/v1/tickets",
        headers=tokens["analyst"],
        json={"subject": "x", "priority": "low", "category": "general"},
    ).json()

    resp = client.patch(
        f"/api/v1/tickets/{ticket['id']}",
        headers=tokens["analyst"],
        json={"assigned_to_id": 9999},
    )
    assert resp.status_code == 400
