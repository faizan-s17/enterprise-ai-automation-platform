"""Document upload, extraction, classification, and analysis.

Uses .txt fixtures (extract_text handles .txt/.md/.csv directly, no PDF/DOCX
parsing library needed) so these tests stay fast and dependency-free, while
still exercising the real extraction -> classify -> analyse pipeline end to
end, the same code path a PDF upload goes through after extract_text runs.
"""

INVOICE_TEXT = (
    "ACME SUPPLIES LTD.\n"
    "INVOICE\n"
    "Invoice Number: INV-2026-0847\n"
    "Invoice Date: 2026-08-13\n"
    "Due Date: 2026-08-27\n"
    "Total due: PKR 824,520\n"
    "Action required: Finance must approve before 2026-08-27.\n"
)


def test_upload_extracts_and_analyses_a_document(client, tokens):
    resp = client.post(
        "/api/v1/documents/upload",
        headers=tokens["analyst"],
        files={"file": ("invoice.txt", INVOICE_TEXT.encode(), "text/plain")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "analyzed"
    assert body["doc_type"] == "invoice"
    assert body["ai_fields"]["reference"] == "INV-2026-0847"
    assert body["ai_fields"]["total_amount"] == 824520.0
    assert body["ai_fields"]["currency"] == "PKR"
    assert "extracted_text" in body


def test_upload_rejects_an_unsupported_file_type(client, tokens):
    resp = client.post(
        "/api/v1/documents/upload",
        headers=tokens["analyst"],
        files={"file": ("archive.zip", b"PK\x03\x04", "application/zip")},
    )
    assert resp.status_code == 415


def test_classification_recognises_a_contract(client, tokens):
    text = (
        "SERVICE AGREEMENT\n"
        "This agreement is entered into by and between the parties below, "
        "who hereby agree to the terms and conditions set out herein.\n"
    )
    resp = client.post(
        "/api/v1/documents/upload",
        headers=tokens["analyst"],
        files={"file": ("agreement.txt", text.encode(), "text/plain")},
    )
    assert resp.status_code == 201
    assert resp.json()["doc_type"] == "contract"


def test_listing_can_be_filtered_by_type_and_status(client, tokens):
    client.post(
        "/api/v1/documents/upload",
        headers=tokens["analyst"],
        files={"file": ("invoice.txt", INVOICE_TEXT.encode(), "text/plain")},
    )

    resp = client.get(
        "/api/v1/documents",
        headers=tokens["analyst"],
        params={"doc_type": "invoice", "status": "analyzed"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["doc_type"] == "invoice"


def test_reanalyse_reruns_analysis_on_stored_text(client, tokens):
    uploaded = client.post(
        "/api/v1/documents/upload",
        headers=tokens["analyst"],
        files={"file": ("invoice.txt", INVOICE_TEXT.encode(), "text/plain")},
    ).json()

    resp = client.post(
        f"/api/v1/documents/{uploaded['id']}/reanalyse", headers=tokens["analyst"]
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "analyzed"


def test_reanalyse_a_missing_document_is_404(client, tokens):
    resp = client.post("/api/v1/documents/999/reanalyse", headers=tokens["analyst"])
    assert resp.status_code == 404


def test_delete_removes_the_document(client, tokens):
    uploaded = client.post(
        "/api/v1/documents/upload",
        headers=tokens["analyst"],
        files={"file": ("invoice.txt", INVOICE_TEXT.encode(), "text/plain")},
    ).json()

    delete = client.delete(
        f"/api/v1/documents/{uploaded['id']}", headers=tokens["analyst"]
    )
    assert delete.status_code == 204

    fetched = client.get(
        f"/api/v1/documents/{uploaded['id']}", headers=tokens["analyst"]
    )
    assert fetched.status_code == 404
