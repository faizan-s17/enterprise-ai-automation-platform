"""Text extraction and AI analysis for uploaded documents."""
from __future__ import annotations

import logging
import re
import zipfile
from pathlib import Path

from app.models import DocumentType
from app.services import ai

log = logging.getLogger(__name__)

SUPPORTED = {".pdf", ".docx", ".txt", ".md", ".csv"}


class UnsupportedDocument(ValueError):
    pass


# ------------------------------------------------------------------ extraction
def extract_text(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf(path)
    if suffix == ".docx":
        return _docx(path)
    if suffix in (".txt", ".md", ".csv"):
        return path.read_text(encoding="utf-8", errors="replace").strip()
    raise UnsupportedDocument(
        f"{suffix or 'file'} is not supported; expected one of "
        f"{', '.join(sorted(SUPPORTED))}"
    )


def _pdf(path: Path) -> str:
    import pymupdf

    parts = []
    with pymupdf.open(path) as doc:
        for page in doc:
            parts.append(page.get_text())
    return "\n".join(parts).strip()


def _docx(path: Path) -> str:
    """Read a .docx without python-docx.

    A .docx is a zip holding WordprocessingML, so pulling word/document.xml and
    flattening it keeps the dependency list smaller and avoids a hard failure
    on files python-docx considers slightly malformed.
    """
    with zipfile.ZipFile(path) as z:
        try:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        except KeyError as exc:
            raise UnsupportedDocument(
                "file is not a Word document (no word/document.xml)"
            ) from exc

    lines = []
    for para in re.split(r"<w:p[ >]", xml)[1:]:
        runs = re.findall(r"<w:t[^>]*>(.*?)</w:t>", para, re.DOTALL)
        line = "".join(runs)
        for entity, char in (
            ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
            ("&quot;", '"'), ("&apos;", "'"),
        ):
            line = line.replace(entity, char)
        if line.strip():
            lines.append(line.strip())
    return "\n".join(lines)


# -------------------------------------------------------------- classification
_TYPE_HINTS: list[tuple[DocumentType, tuple[str, ...]]] = [
    (DocumentType.INVOICE, ("invoice", "amount due", "bill to", "total due")),
    (DocumentType.PURCHASE_ORDER, ("purchase order", "po number", "po-")),
    (DocumentType.CONTRACT, ("agreement", "this contract", "hereby agree",
                             "terms and conditions", "party of the")),
    (DocumentType.RECEIPT, ("receipt", "paid in full", "thank you for your payment")),
    (DocumentType.REPORT, ("report", "summary of findings", "quarterly")),
]


def classify(text: str, filename: str = "") -> DocumentType:
    haystack = f"{filename}\n{text[:4000]}".lower()
    best, best_hits = DocumentType.OTHER, 0
    for doc_type, hints in _TYPE_HINTS:
        hits = sum(1 for h in hints if h in haystack)
        if hits > best_hits:
            best, best_hits = doc_type, hits
    return best


# -------------------------------------------------------------------- analysis
ANALYSIS_SYSTEM = (
    "You analyse business documents for an automation platform. "
    "Reply with a JSON object only, no prose and no markdown fences."
)

ANALYSIS_SCHEMA = """Return exactly this shape:
{
  "summary": "3 to 5 plain sentences describing the document",
  "reference": "document or invoice number, or null",
  "counterparty": "the other organisation named, or null",
  "total_amount": number or null,
  "currency": "ISO code or symbol, or null",
  "key_dates": ["YYYY-MM-DD", ...],
  "action_required": "what someone must do next, or null",
  "risk_flags": ["anything unusual: penalties, auto-renewal, short deadlines"]
}"""


def analyse(text: str, doc_type: DocumentType) -> tuple[str, dict, str]:
    """Return (summary, structured fields, model name).

    Falls back to regex extraction plus an extractive summary when no model is
    configured, so the caller always receives the same shape.
    """
    if not text.strip():
        return "No readable text was extracted from this document.", {}, "none"

    prompt = (
        f"Document type: {doc_type.value}\n\n{ANALYSIS_SCHEMA}\n\n"
        f"Document:\n{text[:12000]}"
    )
    regex_fields = ai.extract_fields(text)
    fallback = {
        "summary": ai.extractive_summary(text),
        **regex_fields,
    }

    data, result = ai.complete_json(prompt, ANALYSIS_SYSTEM, fallback)

    if result.is_fallback:
        return fallback["summary"], regex_fields, "local-fallback"

    summary = str(data.pop("summary", "")).strip() or ai.extractive_summary(text)
    # Regex findings fill gaps the model left null rather than overriding it.
    for key, value in regex_fields.items():
        if data.get(key) in (None, "", [], {}):
            data.setdefault(key, value)
    cleaned = {k: v for k, v in data.items() if v not in (None, "", [], {})}
    return summary, cleaned, result.model
