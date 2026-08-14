"""The AI assistant: grounding, retrieval, and the local fallback's honesty."""


def test_an_unanswerable_question_is_reported_as_ungrounded(client, tokens):
    resp = client.post(
        "/api/v1/assistant/ask",
        headers=tokens["viewer"],
        json={"question": "What is the capital of France?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["grounded"] is False
    assert body["sources"] == []


def test_a_question_matching_a_real_ticket_is_grounded_in_it(client, tokens):
    client.post(
        "/api/v1/tickets",
        headers=tokens["analyst"],
        json={
            "subject": "Server outage in production",
            "priority": "urgent",
            "category": "technical",
        },
    )

    resp = client.post(
        "/api/v1/assistant/ask",
        headers=tokens["viewer"],
        json={"question": "Tell me about the server outage"},
    )
    body = resp.json()
    assert body["grounded"] is True
    assert any(s["type"] == "ticket" for s in body["sources"])


def test_plural_question_matches_a_singular_document_type(client, tokens):
    """Regression test: 'invoices' must match a document whose extracted text
    or classification says 'invoice', not fail to match on the plural s."""
    client.post(
        "/api/v1/documents/upload",
        headers=tokens["analyst"],
        files={
            "file": (
                "inv.txt",
                b"INVOICE\nInvoice Number: INV-1\nTotal due: PKR 500\n",
                "text/plain",
            )
        },
    )

    resp = client.post(
        "/api/v1/assistant/ask",
        headers=tokens["viewer"],
        json={"question": "What invoices do we have on record?"},
    )
    body = resp.json()
    assert body["grounded"] is True
    assert any(s["type"] == "document" for s in body["sources"])


def test_question_by_document_type_alone_matches_even_with_no_keyword_overlap(
    client, tokens
):
    """Regression test: a document classified as a contract should be found
    by 'show me contracts' even if the word 'contract' never appears in its
    text or filename."""
    client.post(
        "/api/v1/documents/upload",
        headers=tokens["analyst"],
        files={
            "file": (
                "deal.txt",
                b"This agreement is entered into by the parties, who hereby "
                b"agree to the terms and conditions herein.",
                "text/plain",
            )
        },
    )

    resp = client.post(
        "/api/v1/assistant/ask",
        headers=tokens["viewer"],
        json={"question": "Show me contracts"},
    )
    body = resp.json()
    assert body["grounded"] is True


def test_suggestions_returns_a_nonempty_list(client, tokens):
    resp = client.get("/api/v1/assistant/suggestions", headers=tokens["viewer"])
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_asking_a_question_is_audited(client, tokens):
    client.post(
        "/api/v1/assistant/ask",
        headers=tokens["viewer"],
        json={"question": "Are there any urgent tickets?"},
    )
    resp = client.get(
        "/api/v1/admin/audit-log",
        headers=tokens["admin"],
        params={"action": "assistant.ask"},
    )
    assert len(resp.json()) == 1
