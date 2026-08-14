"""Seed a demo tenant so the platform is usable the moment it starts."""
import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.models import (
    ApprovalRequest,
    Document,
    DocumentStatus,
    DocumentType,
    Integration,
    IntegrationKind,
    IntegrationStatus,
    Role,
    RunStatus,
    TicketPriority,
    TicketSource,
    TicketStatus,
    User,
    WorkflowRun,
)
from app.services.tickets import create_ticket

log = logging.getLogger(__name__)

DEMO_USERS = [
    ("manager@nexgenautomation.com", "Manager@12345", "Ayesha Khan", "Finance", Role.MANAGER),
    ("analyst@nexgenautomation.com", "Analyst@12345", "Bilal Ahmed", "Operations", Role.ANALYST),
    ("viewer@nexgenautomation.com", "Viewer@12345", "Sana Malik", "Support", Role.VIEWER),
]


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return
        log.info("Empty database detected, seeding demo data")

        admin = User(
            email=settings.SEED_ADMIN_EMAIL.lower(),
            hashed_password=hash_password(settings.SEED_ADMIN_PASSWORD),
            full_name="Platform Administrator",
            department="IT",
            role=Role.ADMIN,
        )
        db.add(admin)

        users = [admin]
        for email, password, name, dept, role in DEMO_USERS:
            u = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=name,
                department=dept,
                role=role,
            )
            db.add(u)
            users.append(u)
        db.commit()
        for u in users:
            db.refresh(u)
        analyst = users[2]

        now = datetime.now(timezone.utc)

        db.add_all([
            Document(
                filename="Invoice-INV-2026-0847.pdf",
                content_type="application/pdf",
                size_bytes=4285,
                doc_type=DocumentType.INVOICE,
                status=DocumentStatus.ANALYZED,
                extracted_text="Meridian Cloud Systems invoice INV-2026-0847 "
                               "total PKR 824,520 due 2026-08-27.",
                ai_summary="- Invoice INV-2026-0847 from Meridian Cloud Systems, "
                           "PKR 824,520.\n- Payment due 2026-08-27 on Net 14 terms.\n"
                           "- Finance must approve before the due date.",
                ai_fields={"reference": "INV-2026-0847", "total_amount": 824520.0,
                           "currency": "PKR", "analysed_by": "seed"},
                uploaded_by_id=analyst.id,
                created_at=now - timedelta(days=2),
                processed_at=now - timedelta(days=2),
            ),
            Document(
                filename="Service-Agreement-2026.docx",
                content_type="application/vnd.openxmlformats-officedocument"
                             ".wordprocessingml.document",
                size_bytes=18422,
                doc_type=DocumentType.CONTRACT,
                status=DocumentStatus.ANALYZED,
                extracted_text="Master services agreement with auto-renewal.",
                ai_summary="- Master services agreement, 12 month term.\n"
                           "- Renews automatically unless cancelled 30 days ahead.\n"
                           "- Review before the renewal window closes.",
                ai_fields={"counterparty": "Northwind Traders",
                           "risk_flags": ["auto-renewal"], "analysed_by": "seed"},
                uploaded_by_id=analyst.id,
                created_at=now - timedelta(days=5),
                processed_at=now - timedelta(days=5),
            ),
        ])
        db.commit()

        create_ticket(db, "Invoice INV-2026-0847 payment overdue",
                      "The invoice passed its due date and a late fee now applies.",
                      source=TicketSource.EMAIL,
                      requester_email="billing@meridiancloud.example",
                      auto_triage=True)
        create_ticket(db, "Cannot access the reporting dashboard",
                      "Login returns a 403 for the whole Operations team.",
                      source=TicketSource.EMAIL,
                      requester_email="ops@nexgenautomation.com",
                      auto_triage=True)
        create_ticket(db, "Quarterly newsletter for review",
                      "FYI, no rush on this one.",
                      source=TicketSource.MANUAL,
                      priority=TicketPriority.LOW, category="general",
                      auto_triage=False)

        resolved = create_ticket(db, "Supplier onboarding for Northwind",
                                 "Vendor paperwork completed.",
                                 source=TicketSource.MANUAL,
                                 priority=TicketPriority.MEDIUM,
                                 category="procurement", auto_triage=False)
        resolved.status = TicketStatus.RESOLVED
        resolved.resolved_at = now - timedelta(days=1)

        db.add_all([
            ApprovalRequest(
                title="Approve payment of invoice INV-2026-0847",
                description="Meridian Cloud Systems, July 2026 services.",
                entity_type="document", entity_id=1,
                amount=824520.0, currency="PKR",
                requested_by_id=analyst.id,
                created_at=now - timedelta(days=1),
            ),
            ApprovalRequest(
                title="Approve stationery purchase order",
                description="Office supplies for the Karachi office.",
                entity_type="document", entity_id=None,
                amount=45000.0, currency="PKR",
                requested_by_id=analyst.id,
                created_at=now - timedelta(hours=6),
            ),
        ])

        for i, (name, status_, mins) in enumerate([
            ("document-intake", RunStatus.SUCCESS, 12),
            ("invoice-approval", RunStatus.SUCCESS, 45),
            ("ticket-triage", RunStatus.SUCCESS, 90),
            ("crm-sync", RunStatus.FAILED, 150),
        ]):
            started = now - timedelta(minutes=mins)
            db.add(WorkflowRun(
                workflow_name=name,
                trigger_source="n8n" if i % 2 else "api",
                status=status_,
                payload={"seeded": True},
                result={} if status_ is RunStatus.FAILED else {"ok": True},
                error="Connection refused by CRM sandbox" if status_ is RunStatus.FAILED else "",
                started_at=started,
                finished_at=started + timedelta(seconds=3),
                duration_ms=3000 + i * 400,
            ))

        for kind, name in [
            (IntegrationKind.CRM, "CRM"),
            (IntegrationKind.ERP, "ERP"),
            (IntegrationKind.GOOGLE_WORKSPACE, "Google Workspace"),
            (IntegrationKind.MICROSOFT_365, "Microsoft 365"),
        ]:
            db.add(Integration(name=name, kind=kind,
                               status=IntegrationStatus.SANDBOX,
                               config={"mode": "sandbox"}))

        db.commit()
        log.info("Seeded %d users, 2 documents, 4 tickets, 2 approvals, "
                 "4 workflow runs, 4 integrations", len(users))
    finally:
        db.close()
