"""Integration adapters: listing, sandbox execution, and error shapes."""


def test_all_four_adapters_are_listed_in_sandbox_mode_by_default(client, tokens):
    resp = client.get("/api/v1/integrations", headers=tokens["viewer"])
    assert resp.status_code == 200
    kinds = {i["kind"] for i in resp.json()}
    assert kinds == {"crm", "erp", "google_workspace", "microsoft_365"}
    assert all(i["mode"] == "sandbox" for i in resp.json())


def test_crm_create_contact_returns_a_sandbox_record(client, tokens):
    resp = client.post(
        "/api/v1/integrations/crm/execute",
        headers=tokens["analyst"],
        json={
            "operation": "create_contact",
            "payload": {"email": "a@example.com", "name": "Test Co"},
        },
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["mode"] == "sandbox"
    assert result["contact"]["email"] == "a@example.com"


def test_sandbox_state_persists_across_calls(client, tokens):
    """Created records should show up in a subsequent list call, which is
    what makes the sandbox usable for demonstrating a workflow end to end."""
    client.post(
        "/api/v1/integrations/crm/execute",
        headers=tokens["analyst"],
        json={"operation": "create_contact", "payload": {"email": "b@example.com"}},
    )
    resp = client.post(
        "/api/v1/integrations/crm/execute",
        headers=tokens["analyst"],
        json={"operation": "list_contacts", "payload": {}},
    )
    emails = [c["email"] for c in resp.json()["result"]["contacts"]]
    assert "b@example.com" in emails


def test_erp_post_invoice_requires_a_reference(client, tokens):
    resp = client.post(
        "/api/v1/integrations/erp/execute",
        headers=tokens["analyst"],
        json={"operation": "post_invoice", "payload": {"amount": 1000}},
    )
    assert resp.status_code == 400


def test_unknown_operation_is_a_400_naming_the_valid_ones(client, tokens):
    resp = client.post(
        "/api/v1/integrations/crm/execute",
        headers=tokens["analyst"],
        json={"operation": "delete_everything", "payload": {}},
    )
    assert resp.status_code == 400
    assert "list_contacts" in resp.json()["detail"]


def test_unknown_integration_is_404(client, tokens):
    resp = client.get("/api/v1/integrations/sap/health", headers=tokens["viewer"])
    assert resp.status_code == 404


def test_viewer_can_read_but_not_execute(client, tokens):
    listing = client.get("/api/v1/integrations", headers=tokens["viewer"])
    assert listing.status_code == 200

    execute = client.post(
        "/api/v1/integrations/crm/execute",
        headers=tokens["viewer"],
        json={"operation": "list_contacts", "payload": {}},
    )
    assert execute.status_code == 403
