import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.user import utcnow


class RunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class IntegrationKind(str, enum.Enum):
    CRM = "crm"
    ERP = "erp"
    GOOGLE_WORKSPACE = "google_workspace"
    MICROSOFT_365 = "microsoft_365"


class IntegrationStatus(str, enum.Enum):
    CONNECTED = "connected"
    SANDBOX = "sandbox"
    ERROR = "error"
    DISABLED = "disabled"


class WorkflowRun(Base):
    """One execution of an automation, whether triggered here or by n8n."""

    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_name: Mapped[str] = mapped_column(String(200), index=True)
    trigger_source: Mapped[str] = mapped_column(String(80), default="api", index=True)

    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus), default=RunStatus.RUNNING, index=True
    )
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")

    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    triggered_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )


class Integration(Base):
    """A connected business system.

    Credentials are never stored here; `config` holds non-secret settings only,
    and secrets stay in the environment.
    """

    __tablename__ = "integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    kind: Mapped[IntegrationKind] = mapped_column(Enum(IntegrationKind), index=True)
    status: Mapped[IntegrationStatus] = mapped_column(
        Enum(IntegrationStatus), default=IntegrationStatus.SANDBOX, index=True
    )
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
