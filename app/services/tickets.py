"""Ticket creation, including AI triage of inbound email."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Ticket, TicketPriority, TicketSource, TicketStatus
from app.services import ai

TRIAGE_SYSTEM = (
    "You triage inbound support and operations email for a business "
    "automation platform. Reply with a JSON object only."
)

TRIAGE_SCHEMA = """Return exactly this shape:
{
  "priority": "low" | "medium" | "high" | "urgent",
  "category": "billing" | "technical" | "contract" | "procurement" | "hr" | "general",
  "reasoning": "one sentence explaining the priority",
  "suggested_action": "the single next step someone should take"
}"""

# Ordered most severe first: the first rule that matches decides, so "outage"
# outranks "invoice" when a message mentions both.
_PRIORITY_RULES: list[tuple[TicketPriority, tuple[str, ...]]] = [
    (TicketPriority.URGENT,
     ("urgent", "asap", "immediately", "outage", "down", "breach",
      "critical", "emergency", "overdue")),
    (TicketPriority.HIGH,
     ("today", "escalate", "deadline", "penalty", "late fee", "blocked",
      "cannot access", "failed")),
    (TicketPriority.LOW,
     ("fyi", "no rush", "whenever", "newsletter", "for your information")),
]

_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("billing", ("invoice", "payment", "billing", "refund", "receipt", "charge")),
    ("contract", ("contract", "agreement", "renewal", "terms", "nda")),
    ("procurement", ("purchase order", "procurement", "supplier", "vendor", "quote")),
    ("technical", ("error", "bug", "outage", "server", "api", "login", "access")),
    ("hr", ("leave", "payroll", "onboarding", "candidate", "interview")),
]


def _rule_triage(subject: str, body: str) -> tuple[TicketPriority, str, str]:
    text = f"{subject}\n{body}".lower()

    priority = TicketPriority.MEDIUM
    matched = ""
    for level, words in _PRIORITY_RULES:
        hit = next((w for w in words if w in text), None)
        if hit:
            priority, matched = level, hit
            break

    # Score every category rather than taking the first rule that matches.
    # "payment system outage" contains both a billing word and two technical
    # ones; first-match-wins filed it under billing, which is the wrong queue.
    category, best = "general", 0
    for name, words in _CATEGORY_RULES:
        hits = sum(1 for w in words if w in text)
        if hits > best:
            category, best = name, hits

    reason = (
        f"Matched the keyword '{matched}', so triaged as {priority.value}."
        if matched
        else "No priority keywords matched, so left at the default of medium."
    )
    return priority, category, reason


def triage(subject: str, body: str) -> tuple[TicketPriority, str, str, bool]:
    """Return (priority, category, reasoning, used_ai)."""
    fallback_priority, fallback_category, fallback_reason = _rule_triage(subject, body)

    prompt = f"{TRIAGE_SCHEMA}\n\nSubject: {subject}\n\nBody:\n{body[:4000]}"
    data, result = ai.complete_json(
        prompt,
        TRIAGE_SYSTEM,
        {
            "priority": fallback_priority.value,
            "category": fallback_category,
            "reasoning": fallback_reason,
        },
    )

    if result.is_fallback:
        return fallback_priority, fallback_category, fallback_reason, False

    try:
        priority = TicketPriority(str(data.get("priority", "")).lower())
    except ValueError:
        priority = fallback_priority

    category = str(data.get("category") or fallback_category).lower()
    reasoning = str(data.get("reasoning") or fallback_reason)
    if data.get("suggested_action"):
        reasoning = f"{reasoning} Next step: {data['suggested_action']}"
    return priority, category, reasoning, True


def next_reference(db: Session) -> str:
    """Human-friendly ticket reference, unique per year.

    A random suffix rather than a running count, because two concurrent
    requests reading the same count would collide on the unique index.
    """
    year = datetime.now(timezone.utc).year
    for _ in range(10):
        ref = f"TKT-{year}-{secrets.randbelow(900000) + 100000}"
        if not db.query(Ticket).filter(Ticket.reference == ref).first():
            return ref
    raise RuntimeError("could not allocate a unique ticket reference")


def create_ticket(
    db: Session,
    subject: str,
    description: str = "",
    *,
    source: TicketSource = TicketSource.MANUAL,
    requester_email: str = "",
    priority: TicketPriority | None = None,
    category: str | None = None,
    document_id: int | None = None,
    created_by_id: int | None = None,
    auto_triage: bool = True,
) -> Ticket:
    """Create a ticket, triaging it when priority and category were not given."""
    reasoning, used_ai = "", False
    if auto_triage and (priority is None or category is None):
        ai_priority, ai_category, reasoning, used_ai = triage(subject, description)
        priority = priority or ai_priority
        category = category or ai_category

    ticket = Ticket(
        reference=next_reference(db),
        subject=subject.strip()[:500] or "(no subject)",
        description=description,
        source=source,
        status=TicketStatus.OPEN,
        priority=priority or TicketPriority.MEDIUM,
        category=(category or "general").strip().lower(),
        ai_classified=used_ai,
        ai_reasoning=reasoning,
        requester_email=requester_email or "",
        document_id=document_id,
        created_by_id=created_by_id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def strip_quoted_reply(body: str) -> str:
    """Drop quoted history so triage reads the new message, not the thread."""
    cut = re.split(
        r"\n-{2,}\s*Original Message|\nOn .{0,120} wrote:|\n>{1,}\s",
        body,
        maxsplit=1,
    )[0]
    return cut.strip()
