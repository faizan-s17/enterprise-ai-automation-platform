"""Approval routing by amount, self-approval, and double-decision guards."""


def create_approval(client, tokens, role, amount):
    return client.post(
        "/api/v1/approvals",
        headers=tokens[role],
        json={"title": "Test request", "amount": amount, "currency": "PKR"},
    ).json()


def test_manager_can_decide_a_request_under_the_threshold(client, tokens):
    approval = create_approval(client, tokens, "analyst", 45_000)

    resp = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        headers=tokens["manager"],
        json={"approved": True, "note": "Within budget"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["decision_note"] == "Within budget"


def test_manager_cannot_decide_a_request_at_or_above_the_threshold(client, tokens):
    approval = create_approval(client, tokens, "analyst", 500_000)

    resp = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        headers=tokens["manager"],
        json={"approved": True},
    )
    assert resp.status_code == 403


def test_admin_can_decide_a_request_above_the_threshold(client, tokens):
    approval = create_approval(client, tokens, "analyst", 824_520)

    resp = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        headers=tokens["admin"],
        json={"approved": True},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_a_request_with_no_amount_only_needs_manager(client, tokens):
    approval = create_approval(client, tokens, "analyst", None)

    resp = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        headers=tokens["manager"],
        json={"approved": True},
    )
    assert resp.status_code == 200


def test_cannot_approve_your_own_request(client, tokens):
    approval = create_approval(client, tokens, "admin", 1000)

    resp = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        headers=tokens["admin"],
        json={"approved": True},
    )
    assert resp.status_code == 403


def test_cannot_decide_the_same_request_twice(client, tokens):
    approval = create_approval(client, tokens, "analyst", 1000)

    first = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        headers=tokens["manager"],
        json={"approved": True},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        headers=tokens["manager"],
        json={"approved": False},
    )
    assert second.status_code == 409


def test_rejecting_a_request_records_the_rejection(client, tokens):
    approval = create_approval(client, tokens, "analyst", 1000)

    resp = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        headers=tokens["manager"],
        json={"approved": False, "note": "Not this quarter"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["decision_note"] == "Not this quarter"


def test_viewer_cannot_raise_an_approval_request(client, tokens):
    resp = client.post(
        "/api/v1/approvals",
        headers=tokens["viewer"],
        json={"title": "x", "amount": 100},
    )
    assert resp.status_code == 403


def test_analyst_cannot_decide_any_request(client, tokens):
    approval = create_approval(client, tokens, "analyst", 1000)

    resp = client.post(
        f"/api/v1/approvals/{approval['id']}/decision",
        headers=tokens["analyst"],
        json={"approved": True},
    )
    assert resp.status_code == 403


def test_listing_can_filter_by_status(client, tokens):
    create_approval(client, tokens, "analyst", 1000)
    approved = create_approval(client, tokens, "analyst", 2000)
    client.post(
        f"/api/v1/approvals/{approved['id']}/decision",
        headers=tokens["manager"],
        json={"approved": True},
    )

    resp = client.get(
        "/api/v1/approvals", headers=tokens["analyst"], params={"status": "approved"}
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
