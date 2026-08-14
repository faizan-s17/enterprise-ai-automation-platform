"""The business AI assistant.

Answers are grounded in what the platform actually holds. The assistant
retrieves matching records first and answers only from them, so it reports
"nothing on record" instead of inventing a plausible figure.
"""
from __future__ import annotations

import re

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import (
    ApprovalRequest,
    ApprovalStatus,
    Document,
    DocumentStatus,
    DocumentType,
    Ticket,
    TicketStatus,
)
from app.services import ai

ASSISTANT_SYSTEM = (
    "You are the assistant for an internal business automation platform. "
    "Answer only from the CONTEXT provided. If the context does not contain "
    "the answer, say so plainly and suggest what the user could search for "
    "instead. Never invent figures, dates, or document references. "
    "Write plain text, no markdown formatting."
)

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "what", "which", "who",
    "how", "many", "much", "do", "does", "did", "of", "for", "in", "on",
    "to", "and", "or", "my", "our", "we", "i", "me", "show", "list", "any",
    "there", "have", "has", "been", "with", "from", "about", "all", "this",
}


def _variants(word: str) -> list[str]:
    """Crude singular/plural pair.

    Asking "what invoices do we have" must match a document whose text says
    "Invoice". A full stemmer is overkill here; handling the plural s and es
    covers the overwhelming majority of real questions.
    """
    forms = [word]
    if word.endswith("ies") and len(word) > 4:
        forms.append(word[:-3] + "y")
    elif word.endswith("es") and len(word) > 3:
        forms.append(word[:-2])
        forms.append(word[:-1])
    elif word.endswith("s") and len(word) > 3:
        forms.append(word[:-1])
    else:
        forms.append(word + "s")
    return forms


def keywords(question: str, limit: int = 6) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9-]{2,}", question.lower())
    seen: list[str] = []
    for w in words:
        if w in STOPWORDS:
            continue
        for form in _variants(w):
            if form not in seen and len(form) > 2:
                seen.append(form)
        if len(seen) >= limit:
            break
    return seen[:limit]


def retrieve(db: Session, question: str, include_documents: bool = True) -> tuple[str, list[dict]]:
    """Gather context and the sources it came from."""
    terms = keywords(question)
    blocks: list[str] = []
    sources: list[dict] = []

    # Counts are cheap and answer a large share of real questions directly.
    stats = {
        "documents_total": db.query(func.count(Document.id)).scalar() or 0,
        "documents_analyzed": db.query(func.count(Document.id))
        .filter(Document.status == DocumentStatus.ANALYZED).scalar() or 0,
        "tickets_open": db.query(func.count(Ticket.id))
        .filter(Ticket.status == TicketStatus.OPEN).scalar() or 0,
        "tickets_total": db.query(func.count(Ticket.id)).scalar() or 0,
        "approvals_pending": db.query(func.count(ApprovalRequest.id))
        .filter(ApprovalRequest.status == ApprovalStatus.PENDING).scalar() or 0,
    }
    blocks.append(
        "PLATFORM TOTALS\n"
        + "\n".join(f"{k.replace('_', ' ')}: {v}" for k, v in stats.items())
    )

    if include_documents and terms:
        filters = []
        for t in terms:
            like = f"%{t}%"
            filters.extend([
                Document.filename.ilike(like),
                Document.ai_summary.ilike(like),
                Document.extracted_text.ilike(like),
            ])
        # Match the document type as well as its text. "Show me contracts"
        # should return the service agreement even though the word "contract"
        # never appears in it: what makes it a contract is its type.
        for doc_type in DocumentType:
            if doc_type.value in terms or doc_type.value.replace("_", " ") in " ".join(terms):
                filters.append(Document.doc_type == doc_type)

        docs = (
            db.query(Document).filter(or_(*filters))
            .order_by(Document.created_at.desc()).limit(5).all()
        )
        for d in docs:
            blocks.append(
                f"DOCUMENT #{d.id} ({d.doc_type.value}) {d.filename}\n"
                f"status: {d.status.value}\n"
                f"summary: {d.ai_summary[:800]}\n"
                f"fields: {d.ai_fields}"
            )
            sources.append({
                "type": "document", "id": d.id,
                "label": d.filename, "doc_type": d.doc_type.value,
            })

    if terms:
        filters = []
        for t in terms:
            like = f"%{t}%"
            filters.extend([Ticket.subject.ilike(like), Ticket.description.ilike(like)])
        tickets = (
            db.query(Ticket).filter(or_(*filters))
            .order_by(Ticket.created_at.desc()).limit(5).all()
        )
        for t in tickets:
            blocks.append(
                f"TICKET {t.reference} [{t.status.value}/{t.priority.value}] "
                f"{t.subject}\n{t.description[:400]}"
            )
            sources.append({
                "type": "ticket", "id": t.id,
                "label": t.reference, "status": t.status.value,
            })

    return "\n\n".join(blocks), sources


def _fallback_answer(question: str, context: str, sources: list[dict]) -> str:
    """Readable answer assembled from context when no model is configured."""
    totals = context.split("\n\n")[0]
    lines = [
        "AI model not configured, so this is a direct read of the platform "
        "records rather than a generated answer.",
        "",
        totals,
    ]
    if sources:
        lines += ["", f"Matching records for your question ({len(sources)}):"]
        lines += [f"- {s['type']} {s['label']}" for s in sources]
    else:
        lines += ["", "No documents or tickets matched the terms in your question."]
    return "\n".join(lines)


def ask(db: Session, question: str, include_documents: bool = True) -> dict:
    context, sources = retrieve(db, question, include_documents)
    prompt = f"CONTEXT\n{context}\n\nQUESTION\n{question}"
    result = ai.complete(prompt, ASSISTANT_SYSTEM)

    if result.is_fallback or not result.text:
        return {
            "question": question,
            "answer": _fallback_answer(question, context, sources),
            "sources": sources,
            "model": "local-fallback",
            # grounded means "specific records backed this answer". Reporting
            # True with zero sources overstates the answer, so both paths use
            # the same test.
            "grounded": bool(sources),
        }

    return {
        "question": question,
        "answer": result.text,
        "sources": sources,
        "model": result.model,
        "grounded": bool(sources),
    }
