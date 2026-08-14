"""Pydantic request and response models.

Kept in one module because the shapes are small and cross-referencing them is
easier than chasing imports across a dozen files.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import (
    ApprovalStatus,
    DocumentStatus,
    DocumentType,
    IntegrationKind,
    IntegrationStatus,
    Role,
    RunStatus,
    TicketPriority,
    TicketSource,
    TicketStatus,
)

ORM = ConfigDict(from_attributes=True)


# --------------------------------------------------------------- auth / users
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = ""
    department: str = ""
    role: Role = Role.VIEWER


class UserUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    role: Role | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = ORM
    id: int
    email: EmailStr
    full_name: str
    department: str
    role: Role
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


# ------------------------------------------------------------------ documents
class DocumentOut(BaseModel):
    model_config = ORM
    id: int
    filename: str
    content_type: str
    size_bytes: int
    doc_type: DocumentType
    status: DocumentStatus
    ai_summary: str
    ai_fields: dict[str, Any]
    error: str
    uploaded_by_id: int | None
    created_at: datetime
    processed_at: datetime | None


class DocumentDetail(DocumentOut):
    extracted_text: str


# -------------------------------------------------------------------- tickets
class TicketCreate(BaseModel):
    subject: str
    description: str = ""
    requester_email: EmailStr | None = None
    priority: TicketPriority | None = None
    category: str | None = None
    source: TicketSource = TicketSource.MANUAL
    document_id: int | None = None


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category: str | None = None
    assigned_to_id: int | None = None


class TicketOut(BaseModel):
    model_config = ORM
    id: int
    reference: str
    subject: str
    description: str
    source: TicketSource
    status: TicketStatus
    priority: TicketPriority
    category: str
    ai_classified: bool
    ai_reasoning: str
    requester_email: str
    assigned_to_id: int | None
    document_id: int | None
    created_at: datetime
    resolved_at: datetime | None


class InboundEmail(BaseModel):
    """Payload an email automation posts in to raise a ticket."""

    from_email: EmailStr
    subject: str
    body: str = ""
    received_at: datetime | None = None


# ------------------------------------------------------------------ approvals
class ApprovalCreate(BaseModel):
    title: str
    description: str = ""
    entity_type: str = "document"
    entity_id: int | None = None
    amount: float | None = None
    currency: str = "PKR"


class ApprovalDecision(BaseModel):
    approved: bool
    note: str = ""


class ApprovalOut(BaseModel):
    model_config = ORM
    id: int
    title: str
    description: str
    entity_type: str
    entity_id: int | None
    amount: float | None
    currency: str
    status: ApprovalStatus
    decision_note: str
    requested_by_id: int | None
    approver_id: int | None
    decided_by_id: int | None
    created_at: datetime
    decided_at: datetime | None


# ------------------------------------------------------------------ assistant
class AssistantQuery(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    include_documents: bool = True


class AssistantAnswer(BaseModel):
    question: str
    answer: str
    sources: list[dict[str, Any]] = []
    model: str
    grounded: bool


# -------------------------------------------------------------------- reports
class ReportRequest(BaseModel):
    kind: str = "operations"
    days: int = Field(default=30, ge=1, le=365)


class ReportOut(BaseModel):
    model_config = ORM
    id: int
    title: str
    kind: str
    period_start: datetime | None
    period_end: datetime | None
    metrics: dict[str, Any]
    narrative: str
    created_at: datetime


# ------------------------------------------------------------------ workflows
class WorkflowTrigger(BaseModel):
    workflow_name: str
    payload: dict[str, Any] = {}


class WorkflowRunOut(BaseModel):
    model_config = ORM
    id: int
    workflow_name: str
    trigger_source: str
    status: RunStatus
    payload: dict[str, Any]
    result: dict[str, Any]
    error: str
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None


# --------------------------------------------------------------- integrations
class IntegrationOut(BaseModel):
    model_config = ORM
    id: int
    name: str
    kind: IntegrationKind
    status: IntegrationStatus
    config: dict[str, Any]
    last_sync_at: datetime | None


# ----------------------------------------------------------------- dashboards
class DashboardStats(BaseModel):
    users: int
    documents: int
    documents_analyzed: int
    tickets_open: int
    tickets_total: int
    approvals_pending: int
    workflow_runs_today: int
    workflow_success_rate: float
    integrations_connected: int
    ai_enabled: bool
