from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

import httpx

from app.config import settings
from app.core.deps import get_current_user, record_audit, require_analyst
from app.database import get_db
from app.models import RunStatus, User, WorkflowRun
from app.schemas import WorkflowRunOut, WorkflowTrigger

router = APIRouter(prefix="/workflows", tags=["Workflow Automation"])


@router.post("/trigger", response_model=WorkflowRunOut,
             status_code=status.HTTP_201_CREATED)
def trigger_workflow(
    payload: WorkflowTrigger,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    """Start a workflow and record the run.

    Posts to n8n when N8N_WEBHOOK_URL is set. Without it the run is still
    recorded and marked as simulated, so the monitoring surface works before
    n8n is connected.
    """
    run = WorkflowRun(
        workflow_name=payload.workflow_name,
        trigger_source="api",
        status=RunStatus.RUNNING,
        payload=payload.payload,
        triggered_by_id=user.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    started = datetime.now(timezone.utc)
    try:
        if settings.N8N_WEBHOOK_URL:
            resp = httpx.post(
                settings.N8N_WEBHOOK_URL,
                json={"workflow": payload.workflow_name, **payload.payload},
                timeout=30.0,
            )
            resp.raise_for_status()
            body = resp.json() if resp.content else {}
            run.result = body if isinstance(body, dict) else {"response": body}
            run.status = RunStatus.SUCCESS
        else:
            run.result = {
                "simulated": True,
                "note": "N8N_WEBHOOK_URL is not configured, so the run was "
                        "recorded without calling n8n.",
                "workflow": payload.workflow_name,
            }
            run.status = RunStatus.SUCCESS
    except Exception as exc:
        run.status = RunStatus.FAILED
        run.error = str(exc)[:2000]
    finally:
        finished = datetime.now(timezone.utc)
        run.finished_at = finished
        run.duration_ms = int((finished - started).total_seconds() * 1000)
        db.commit()
        db.refresh(run)

    record_audit(db, "workflow.trigger", user, "workflow_run", run.id,
                 {"workflow": payload.workflow_name, "status": run.status.value},
                 request)
    return run


@router.post("/callback", response_model=WorkflowRunOut,
             status_code=status.HTTP_201_CREATED)
def workflow_callback(
    payload: WorkflowTrigger,
    request: Request,
    db: Session = Depends(get_db),
):
    """Record a run that started outside the platform.

    n8n posts here when one of its workflows completes, so externally
    triggered automations appear on the same dashboard. Unauthenticated for
    the same reason as the inbound email route, with the same caveat.
    """
    now = datetime.now(timezone.utc)
    run = WorkflowRun(
        workflow_name=payload.workflow_name,
        trigger_source="n8n",
        status=RunStatus.SUCCESS,
        payload=payload.payload,
        result=payload.payload.get("result", {}) if isinstance(
            payload.payload.get("result"), dict) else {},
        started_at=now,
        finished_at=now,
        duration_ms=payload.payload.get("duration_ms"),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    record_audit(db, "workflow.callback", None, "workflow_run", run.id,
                 {"workflow": payload.workflow_name}, request)
    return run


@router.get("/runs", response_model=list[WorkflowRunOut])
def list_runs(
    workflow_name: str | None = None,
    run_status: RunStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(WorkflowRun)
    if workflow_name:
        q = q.filter(WorkflowRun.workflow_name == workflow_name)
    if run_status is not None:
        q = q.filter(WorkflowRun.status == run_status)
    return (q.order_by(WorkflowRun.started_at.desc())
             .offset(offset).limit(limit).all())


@router.get("/runs/{run_id}", response_model=WorkflowRunOut)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return run
