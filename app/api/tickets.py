from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, record_audit, require_analyst
from app.database import get_db
from app.models import Ticket, TicketPriority, TicketSource, TicketStatus, User
from app.schemas import InboundEmail, TicketCreate, TicketOut, TicketUpdate
from app.services import tickets as ticketsvc

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    ticket = ticketsvc.create_ticket(
        db,
        subject=payload.subject,
        description=payload.description,
        source=payload.source,
        requester_email=payload.requester_email or "",
        priority=payload.priority,
        category=payload.category,
        document_id=payload.document_id,
        created_by_id=user.id,
    )
    record_audit(db, "ticket.create", user, "ticket", ticket.id,
                 {"reference": ticket.reference}, request)
    return ticket


@router.post("/inbound-email", response_model=TicketOut,
             status_code=status.HTTP_201_CREATED)
def inbound_email(
    payload: InboundEmail,
    request: Request,
    db: Session = Depends(get_db),
):
    """Raise a ticket from an inbound email.

    Deliberately unauthenticated so a mail automation (n8n, a webhook, a
    forwarding rule) can post here without holding a user token. In a real
    deployment this route would sit behind a shared secret or network policy;
    that limitation is recorded in the technical documentation.
    """
    body = ticketsvc.strip_quoted_reply(payload.body)
    ticket = ticketsvc.create_ticket(
        db,
        subject=payload.subject,
        description=body,
        source=TicketSource.EMAIL,
        requester_email=payload.from_email,
    )
    record_audit(db, "ticket.inbound_email", None, "ticket", ticket.id,
                 {"from": payload.from_email, "reference": ticket.reference}, request)
    return ticket


@router.get("", response_model=list[TicketOut])
def list_tickets(
    ticket_status: TicketStatus | None = Query(None, alias="status"),
    priority: TicketPriority | None = None,
    category: str | None = None,
    assigned_to_id: int | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Ticket)
    if ticket_status is not None:
        q = q.filter(Ticket.status == ticket_status)
    if priority is not None:
        q = q.filter(Ticket.priority == priority)
    if category:
        q = q.filter(Ticket.category == category.lower())
    if assigned_to_id is not None:
        q = q.filter(Ticket.assigned_to_id == assigned_to_id)
    return q.order_by(Ticket.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    changes = payload.model_dump(exclude_unset=True)
    if "assigned_to_id" in changes and changes["assigned_to_id"] is not None:
        if not db.query(User).filter(User.id == changes["assigned_to_id"]).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign the ticket to a user that does not exist",
            )

    for field, value in changes.items():
        setattr(ticket, field, value)

    # Stamp the resolution time once, when it first reaches a closed state.
    closed = {TicketStatus.RESOLVED, TicketStatus.CLOSED}
    if ticket.status in closed and ticket.resolved_at is None:
        ticket.resolved_at = datetime.now(timezone.utc)
    elif ticket.status not in closed:
        ticket.resolved_at = None

    db.commit()
    db.refresh(ticket)
    record_audit(db, "ticket.update", user, "ticket", ticket.id,
                 {k: (v.value if hasattr(v, "value") else v)
                  for k, v in changes.items()}, request)
    return ticket
