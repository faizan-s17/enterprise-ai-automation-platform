"""Metric collection and AI narrative for business reports."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    ApprovalRequest,
    ApprovalStatus,
    Document,
    DocumentStatus,
    RunStatus,
    Ticket,
    TicketPriority,
    TicketStatus,
    User,
    WorkflowRun,
)
from app.services import ai

NARRATIVE_SYSTEM = (
    "You write short operations reports for business leadership. "
    "Work only from the metrics given. Do not invent numbers. "
    "Write plain text in three short paragraphs: what happened, what stands "
    "out, and what to do next. No markdown formatting."
)


def collect_metrics(db: Session, days: int = 30) -> dict:
    since = datetime.now(timezone.utc) - timedelta(days=days)

    docs_total = db.query(func.count(Document.id)).filter(
        Document.created_at >= since).scalar() or 0
    docs_analyzed = db.query(func.count(Document.id)).filter(
        Document.created_at >= since,
        Document.status == DocumentStatus.ANALYZED).scalar() or 0
    docs_failed = db.query(func.count(Document.id)).filter(
        Document.created_at >= since,
        Document.status == DocumentStatus.FAILED).scalar() or 0

    tickets_total = db.query(func.count(Ticket.id)).filter(
        Ticket.created_at >= since).scalar() or 0
    tickets_open = db.query(func.count(Ticket.id)).filter(
        Ticket.created_at >= since,
        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])).scalar() or 0
    tickets_urgent = db.query(func.count(Ticket.id)).filter(
        Ticket.created_at >= since,
        Ticket.priority == TicketPriority.URGENT).scalar() or 0

    by_category = dict(
        db.query(Ticket.category, func.count(Ticket.id))
        .filter(Ticket.created_at >= since)
        .group_by(Ticket.category).all()
    )

    approvals_total = db.query(func.count(ApprovalRequest.id)).filter(
        ApprovalRequest.created_at >= since).scalar() or 0
    approvals_pending = db.query(func.count(ApprovalRequest.id)).filter(
        ApprovalRequest.status == ApprovalStatus.PENDING).scalar() or 0
    approvals_approved = db.query(func.count(ApprovalRequest.id)).filter(
        ApprovalRequest.created_at >= since,
        ApprovalRequest.status == ApprovalStatus.APPROVED).scalar() or 0

    runs_total = db.query(func.count(WorkflowRun.id)).filter(
        WorkflowRun.started_at >= since).scalar() or 0
    runs_ok = db.query(func.count(WorkflowRun.id)).filter(
        WorkflowRun.started_at >= since,
        WorkflowRun.status == RunStatus.SUCCESS).scalar() or 0
    avg_ms = db.query(func.avg(WorkflowRun.duration_ms)).filter(
        WorkflowRun.started_at >= since,
        WorkflowRun.duration_ms.isnot(None)).scalar()

    approved_value = db.query(func.sum(ApprovalRequest.amount)).filter(
        ApprovalRequest.created_at >= since,
        ApprovalRequest.status == ApprovalStatus.APPROVED).scalar()

    return {
        "period_days": days,
        "users_active": db.query(func.count(User.id)).filter(
            User.is_active.is_(True)).scalar() or 0,
        "documents_total": docs_total,
        "documents_analyzed": docs_analyzed,
        "documents_failed": docs_failed,
        "document_success_rate": round(docs_analyzed / docs_total * 100, 1) if docs_total else 0.0,
        "tickets_total": tickets_total,
        "tickets_open": tickets_open,
        "tickets_urgent": tickets_urgent,
        "tickets_by_category": by_category,
        "approvals_total": approvals_total,
        "approvals_pending": approvals_pending,
        "approvals_approved": approvals_approved,
        "approved_value": float(approved_value) if approved_value else 0.0,
        "workflow_runs": runs_total,
        "workflow_success_rate": round(runs_ok / runs_total * 100, 1) if runs_total else 0.0,
        "workflow_avg_ms": int(avg_ms) if avg_ms else 0,
    }


def _fallback_narrative(m: dict) -> str:
    """Deterministic narrative so a report is still useful without a model."""
    lines = [
        f"Over the last {m['period_days']} days the platform processed "
        f"{m['documents_total']} documents, of which {m['documents_analyzed']} "
        f"were analysed successfully ({m['document_success_rate']}%). "
        f"{m['tickets_total']} tickets were raised and {m['tickets_open']} remain open. "
        f"{m['workflow_runs']} automation runs completed at a "
        f"{m['workflow_success_rate']}% success rate.",
    ]

    notes = []
    if m["tickets_urgent"]:
        notes.append(f"{m['tickets_urgent']} tickets were triaged as urgent")
    if m["approvals_pending"]:
        notes.append(f"{m['approvals_pending']} approvals are still awaiting a decision")
    if m["documents_failed"]:
        notes.append(f"{m['documents_failed']} documents failed to process")
    if m["approved_value"]:
        notes.append(f"approved requests carried a total value of {m['approved_value']:,.0f}")
    lines.append(
        ("Worth noting: " + "; ".join(notes) + ".") if notes
        else "Nothing in the period stands out as anomalous."
    )

    actions = []
    if m["approvals_pending"]:
        actions.append("clear the pending approval queue")
    if m["documents_failed"]:
        actions.append("review the documents that failed extraction")
    if m["workflow_success_rate"] and m["workflow_success_rate"] < 90:
        actions.append("investigate the automation failure rate")
    lines.append(
        ("Suggested next steps: " + ", ".join(actions) + ".") if actions
        else "No corrective action is indicated by these figures."
    )
    return "\n\n".join(lines)


def generate_narrative(metrics: dict) -> tuple[str, str]:
    """Return (narrative, model name)."""
    lines = [f"{k}: {v}" for k, v in metrics.items()]
    prompt = "METRICS\n" + "\n".join(lines)
    result = ai.complete(prompt, NARRATIVE_SYSTEM)
    if result.is_fallback or not result.text:
        return _fallback_narrative(metrics), "local-fallback"
    return result.text, result.model
