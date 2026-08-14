"""SQLAlchemy models.

Imported as a package so `Base.metadata` knows every table before create_all.
"""
from app.models.approval import ApprovalRequest, ApprovalStatus
from app.models.audit import AuditLog, Report
from app.models.document import Document, DocumentStatus, DocumentType
from app.models.ticket import Ticket, TicketPriority, TicketSource, TicketStatus
from app.models.user import Role, User
from app.models.workflow import (
    Integration,
    IntegrationKind,
    IntegrationStatus,
    RunStatus,
    WorkflowRun,
)

__all__ = [
    "ApprovalRequest",
    "ApprovalStatus",
    "AuditLog",
    "Report",
    "Document",
    "DocumentStatus",
    "DocumentType",
    "Ticket",
    "TicketPriority",
    "TicketSource",
    "TicketStatus",
    "Role",
    "User",
    "Integration",
    "IntegrationKind",
    "IntegrationStatus",
    "RunStatus",
    "WorkflowRun",
]
