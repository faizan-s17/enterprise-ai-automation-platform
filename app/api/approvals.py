from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, record_audit, require_analyst
from app.database import get_db
from app.models import ApprovalRequest, ApprovalStatus, Role, User
from app.schemas import ApprovalCreate, ApprovalDecision, ApprovalOut

router = APIRouter(prefix="/approvals", tags=["Approvals"])

# Requests at or above this value need an admin rather than a manager.
ADMIN_THRESHOLD = 500_000


def required_role_for(amount: float | None) -> Role:
    if amount is not None and amount >= ADMIN_THRESHOLD:
        return Role.ADMIN
    return Role.MANAGER


@router.post("", response_model=ApprovalOut, status_code=status.HTTP_201_CREATED)
def create_approval(
    payload: ApprovalCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    approval = ApprovalRequest(
        title=payload.title,
        description=payload.description,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        amount=payload.amount,
        currency=payload.currency,
        requested_by_id=user.id,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    record_audit(db, "approval.create", user, "approval", approval.id,
                 {"amount": payload.amount, "currency": payload.currency}, request)
    return approval


@router.get("", response_model=list[ApprovalOut])
def list_approvals(
    approval_status: ApprovalStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ApprovalRequest)
    if approval_status is not None:
        q = q.filter(ApprovalRequest.status == approval_status)
    return (q.order_by(ApprovalRequest.created_at.desc())
             .offset(offset).limit(limit).all())


@router.get("/{approval_id}", response_model=ApprovalOut)
def get_approval(
    approval_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    approval = db.query(ApprovalRequest).filter(
        ApprovalRequest.id == approval_id).first()
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    return approval


@router.post("/{approval_id}/decision", response_model=ApprovalOut)
def decide(
    approval_id: int,
    payload: ApprovalDecision,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Approve or reject.

    Two rules are enforced here rather than left to the caller: the approver
    must hold the role the amount demands, and nobody may approve their own
    request.
    """
    approval = db.query(ApprovalRequest).filter(
        ApprovalRequest.id == approval_id).first()
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This request was already {approval.status.value}",
        )

    amount = float(approval.amount) if approval.amount is not None else None
    needed = required_role_for(amount)
    if not user.role.can_act_as(needed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Requests of {amount:,.0f} {approval.currency} require the "
                f"{needed.value} role; your role is {user.role.value}"
                if amount is not None else
                f"This decision requires the {needed.value} role"
            ),
        )

    if approval.requested_by_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot decide on a request you raised yourself",
        )

    approval.status = (
        ApprovalStatus.APPROVED if payload.approved else ApprovalStatus.REJECTED
    )
    approval.decision_note = payload.note
    approval.decided_by_id = user.id
    approval.approver_id = user.id
    approval.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(approval)

    record_audit(db, f"approval.{approval.status.value}", user, "approval",
                 approval.id, {"note": payload.note, "amount": amount}, request)
    return approval
