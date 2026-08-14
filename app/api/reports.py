from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, record_audit, require_manager
from app.database import get_db
from app.models import Report, User
from app.schemas import ReportOut, ReportRequest
from app.services import reports as reportsvc

router = APIRouter(prefix="/reports", tags=["Reports & Insights"])


@router.post("/generate", response_model=ReportOut,
             status_code=status.HTTP_201_CREATED)
def generate_report(
    payload: ReportRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    """Collect metrics for the period and write a narrative over them."""
    metrics = reportsvc.collect_metrics(db, payload.days)
    narrative, model = reportsvc.generate_narrative(metrics)

    end = datetime.now(timezone.utc)
    report = Report(
        title=f"{payload.kind.replace('_', ' ').title()} report, last {payload.days} days",
        kind=payload.kind,
        period_start=end - timedelta(days=payload.days),
        period_end=end,
        metrics={**metrics, "generated_by_model": model},
        narrative=narrative,
        generated_by_id=user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    record_audit(db, "report.generate", user, "report", report.id,
                 {"kind": payload.kind, "days": payload.days, "model": model}, request)
    return report


@router.get("/metrics")
def live_metrics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Metrics without persisting a report. Feeds the dashboard charts."""
    return reportsvc.collect_metrics(db, days)


@router.get("", response_model=list[ReportOut])
def list_reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return (db.query(Report).order_by(Report.created_at.desc())
              .offset(offset).limit(limit).all())


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
