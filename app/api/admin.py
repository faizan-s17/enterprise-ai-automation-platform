from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user, require_admin
from app.database import get_db
from app.integrations.adapters import all_adapters
from app.models import (
    ApprovalRequest,
    ApprovalStatus,
    AuditLog,
    Document,
    DocumentStatus,
    RunStatus,
    Ticket,
    TicketStatus,
    User,
    WorkflowRun,
)
from app.schemas import DashboardStats

router = APIRouter(prefix="/admin", tags=["Admin & Analytics"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    """Headline counters for the dashboard."""
    since = datetime.now(timezone.utc) - timedelta(days=1)

    runs_today = db.query(func.count(WorkflowRun.id)).filter(
        WorkflowRun.started_at >= since).scalar() or 0
    runs_ok = db.query(func.count(WorkflowRun.id)).filter(
        WorkflowRun.started_at >= since,
        WorkflowRun.status == RunStatus.SUCCESS).scalar() or 0

    return DashboardStats(
        users=db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0,
        documents=db.query(func.count(Document.id)).scalar() or 0,
        documents_analyzed=db.query(func.count(Document.id)).filter(
            Document.status == DocumentStatus.ANALYZED).scalar() or 0,
        tickets_open=db.query(func.count(Ticket.id)).filter(
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
        ).scalar() or 0,
        tickets_total=db.query(func.count(Ticket.id)).scalar() or 0,
        approvals_pending=db.query(func.count(ApprovalRequest.id)).filter(
            ApprovalRequest.status == ApprovalStatus.PENDING).scalar() or 0,
        workflow_runs_today=runs_today,
        workflow_success_rate=round(runs_ok / runs_today * 100, 1) if runs_today else 0.0,
        integrations_connected=sum(1 for a in all_adapters() if a.configured),
        ai_enabled=settings.ai_enabled,
    )


@router.get("/audit-log")
def audit_log(
    action: str | None = None,
    actor_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Audit trail. Admin only, since it records everyone's activity."""
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if actor_id is not None:
        q = q.filter(AuditLog.actor_id == actor_id)
    entries = (q.order_by(AuditLog.created_at.desc())
                .offset(offset).limit(limit).all())
    return [
        {
            "id": e.id,
            "action": e.action,
            "actor_id": e.actor_id,
            "actor_email": e.actor.email if e.actor else None,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "detail": e.detail,
            "ip_address": e.ip_address,
            "created_at": e.created_at,
        }
        for e in entries
    ]


@router.get("/activity")
def activity_timeline(
    days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Per-day counts for the dashboard charts.

    Grouped in Python rather than SQL because date truncation syntax differs
    between SQLite and PostgreSQL, and the platform supports both.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    buckets: dict[str, dict[str, int]] = {}

    def bucket(day: str) -> dict[str, int]:
        return buckets.setdefault(
            day, {"documents": 0, "tickets": 0, "workflow_runs": 0}
        )

    for (created,) in db.query(Document.created_at).filter(
            Document.created_at >= since).all():
        bucket(created.date().isoformat())["documents"] += 1
    for (created,) in db.query(Ticket.created_at).filter(
            Ticket.created_at >= since).all():
        bucket(created.date().isoformat())["tickets"] += 1
    for (started,) in db.query(WorkflowRun.started_at).filter(
            WorkflowRun.started_at >= since).all():
        bucket(started.date().isoformat())["workflow_runs"] += 1

    return [{"date": day, **counts} for day, counts in sorted(buckets.items())]
