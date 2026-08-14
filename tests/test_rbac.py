"""Role gating, exercised across representative routes from every tier.

One `require_role` dependency backs every gated route (see app/core/deps.py),
so this suite checks it works correctly rather than re-testing each of the
~30 gated endpoints individually.
"""
import pytest


@pytest.mark.parametrize("role", ["viewer", "analyst", "manager"])
def test_non_admin_roles_cannot_list_users(client, tokens, role):
    resp = client.get("/api/v1/users", headers=tokens[role])
    assert resp.status_code == 403


def test_admin_can_list_users(client, tokens):
    resp = client.get("/api/v1/users", headers=tokens["admin"])
    assert resp.status_code == 200
    assert len(resp.json()) == 4


def test_forbidden_response_names_the_required_role(client, tokens):
    resp = client.get("/api/v1/users", headers=tokens["viewer"])
    assert "admin" in resp.json()["detail"]
    assert "viewer" in resp.json()["detail"]


def test_viewer_can_read_but_not_write_documents(client, tokens):
    listing = client.get("/api/v1/documents", headers=tokens["viewer"])
    assert listing.status_code == 200

    upload = client.post(
        "/api/v1/documents/upload",
        headers=tokens["viewer"],
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert upload.status_code == 403


def test_analyst_can_upload_documents(client, tokens):
    resp = client.post(
        "/api/v1/documents/upload",
        headers=tokens["analyst"],
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 201


def test_viewer_cannot_generate_reports(client, tokens):
    resp = client.post(
        "/api/v1/reports/generate",
        headers=tokens["viewer"],
        json={"kind": "operations", "days": 30},
    )
    assert resp.status_code == 403


def test_manager_can_generate_reports(client, tokens):
    resp = client.post(
        "/api/v1/reports/generate",
        headers=tokens["manager"],
        json={"kind": "operations", "days": 30},
    )
    assert resp.status_code == 201


def test_admin_can_act_as_every_lower_role(client, tokens):
    """The hierarchy means admin should pass a manager-level gate too."""
    resp = client.post(
        "/api/v1/reports/generate",
        headers=tokens["admin"],
        json={"kind": "operations", "days": 7},
    )
    assert resp.status_code == 201


def test_admin_cannot_change_their_own_role(client, tokens, users):
    resp = client.patch(
        f"/api/v1/users/{users['admin'].id}",
        headers=tokens["admin"],
        json={"role": "viewer"},
    )
    assert resp.status_code == 400


def test_admin_cannot_deactivate_themselves(client, tokens, users):
    resp = client.patch(
        f"/api/v1/users/{users['admin'].id}",
        headers=tokens["admin"],
        json={"is_active": False},
    )
    assert resp.status_code == 400


def test_admin_can_change_another_users_role(client, tokens, users):
    resp = client.patch(
        f"/api/v1/users/{users['viewer'].id}",
        headers=tokens["admin"],
        json={"role": "analyst"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "analyst"


def test_user_can_read_their_own_profile_but_not_someone_elses(client, tokens, users):
    own = client.get(f"/api/v1/users/{users['viewer'].id}", headers=tokens["viewer"])
    assert own.status_code == 200

    other = client.get(f"/api/v1/users/{users['admin'].id}", headers=tokens["viewer"])
    assert other.status_code == 403
