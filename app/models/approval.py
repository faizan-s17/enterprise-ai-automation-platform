import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.user import utcnow


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalRequest(Base):
    """A decision a person has to make, raised against any entity.

    entity_type / entity_id form a loose polymorphic link rather than a real
    foreign key, so the same approval flow covers documents, tickets, and
    anything added later without further schema changes.
    """

    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")

    entity_type: Mapped[str] = mapped_column(String(60), default="document", index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Drives routing: requests above a threshold need a manager or admin.
    amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="PKR")

    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True
    )
    decision_note: Mapped[str] = mapped_column(Text, default="")

    requested_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    approver_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    decided_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    requested_by = relationship("User", foreign_keys=[requested_by_id])
    approver = relationship("User", foreign_keys=[approver_id])
    decided_by = relationship("User", foreign_keys=[decided_by_id])
