"""Aggregates every router under the versioned API prefix."""
from fastapi import APIRouter

from app.api import (
    admin,
    approvals,
    assistant,
    auth,
    documents,
    integrations,
    reports,
    tickets,
    users,
    workflows,
)

api_router = APIRouter()
for module in (
    auth, users, documents, tickets, approvals,
    assistant, reports, workflows, integrations, admin,
):
    api_router.include_router(module.router)
