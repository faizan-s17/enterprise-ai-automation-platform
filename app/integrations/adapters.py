"""Concrete adapters for CRM, ERP, Google Workspace and Microsoft 365.

Sandbox data lives in module-level dictionaries so operations are genuinely
stateful within a run: create a CRM contact and the next list call returns it.
That makes the sandbox useful for demonstrating a workflow end to end rather
than returning a fixed canned payload.
"""
from __future__ import annotations

import itertools
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import settings
from app.integrations.base import BaseAdapter, IntegrationError
from app.models import IntegrationKind

_ids = itertools.count(1000)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------------ CRM
_CRM_CONTACTS: dict[int, dict] = {}
_CRM_DEALS: dict[int, dict] = {}


class CRMAdapter(BaseAdapter):
    kind = IntegrationKind.CRM
    name = "CRM"

    @property
    def configured(self) -> bool:
        return bool(settings.CRM_API_KEY and settings.CRM_BASE_URL)

    def capabilities(self) -> list[str]:
        return ["list_contacts", "create_contact", "list_deals", "create_deal"]

    def health(self) -> dict[str, Any]:
        if not self.configured:
            return {"ok": True, "mode": "sandbox",
                    "contacts": len(_CRM_CONTACTS), "deals": len(_CRM_DEALS)}
        try:
            r = httpx.get(f"{settings.CRM_BASE_URL.rstrip('/')}/ping",
                          headers=self._headers(), timeout=8.0)
            return {"ok": r.status_code < 400, "mode": "live",
                    "status_code": r.status_code}
        except httpx.HTTPError as exc:
            return {"ok": False, "mode": "live", "error": str(exc)}

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.CRM_API_KEY}"}

    def op_list_contacts(self, payload: dict) -> dict:
        if self.configured:
            return self._get("/contacts", payload)
        return {"mode": "sandbox", "contacts": list(_CRM_CONTACTS.values())}

    def op_create_contact(self, payload: dict) -> dict:
        email = payload.get("email")
        if not email:
            raise IntegrationError("create_contact requires 'email'")
        if self.configured:
            return self._post("/contacts", payload)
        cid = next(_ids)
        record = {
            "id": cid, "email": email,
            "name": payload.get("name", ""),
            "company": payload.get("company", ""),
            "created_at": _now(),
        }
        _CRM_CONTACTS[cid] = record
        return {"mode": "sandbox", "contact": record}

    def op_list_deals(self, payload: dict) -> dict:
        if self.configured:
            return self._get("/deals", payload)
        return {"mode": "sandbox", "deals": list(_CRM_DEALS.values())}

    def op_create_deal(self, payload: dict) -> dict:
        if self.configured:
            return self._post("/deals", payload)
        did = next(_ids)
        record = {
            "id": did,
            "title": payload.get("title", "Untitled deal"),
            "amount": payload.get("amount", 0),
            "currency": payload.get("currency", "PKR"),
            "stage": payload.get("stage", "qualification"),
            "created_at": _now(),
        }
        _CRM_DEALS[did] = record
        return {"mode": "sandbox", "deal": record}

    def _get(self, path: str, params: dict) -> dict:
        r = httpx.get(f"{settings.CRM_BASE_URL.rstrip('/')}{path}",
                      headers=self._headers(), params=params, timeout=15.0)
        r.raise_for_status()
        return {"mode": "live", **r.json()}

    def _post(self, path: str, body: dict) -> dict:
        r = httpx.post(f"{settings.CRM_BASE_URL.rstrip('/')}{path}",
                       headers=self._headers(), json=body, timeout=15.0)
        r.raise_for_status()
        return {"mode": "live", **r.json()}


# ------------------------------------------------------------------------ ERP
_ERP_INVOICES: dict[int, dict] = {}


class ERPAdapter(BaseAdapter):
    kind = IntegrationKind.ERP
    name = "ERP"

    @property
    def configured(self) -> bool:
        return bool(settings.ERP_API_KEY and settings.ERP_BASE_URL)

    def capabilities(self) -> list[str]:
        return ["list_invoices", "post_invoice", "get_stock", "cost_centres"]

    def health(self) -> dict[str, Any]:
        return {"ok": True, "mode": "live" if self.configured else "sandbox",
                "invoices": len(_ERP_INVOICES)}

    def op_list_invoices(self, payload: dict) -> dict:
        return {"mode": self._mode(), "invoices": list(_ERP_INVOICES.values())}

    def op_post_invoice(self, payload: dict) -> dict:
        ref = payload.get("reference")
        if not ref:
            raise IntegrationError("post_invoice requires 'reference'")
        iid = next(_ids)
        record = {
            "id": iid, "reference": ref,
            "amount": payload.get("amount", 0),
            "currency": payload.get("currency", "PKR"),
            "supplier": payload.get("supplier", ""),
            "due_date": payload.get("due_date"),
            "posted_at": _now(),
            "ledger": payload.get("cost_centre", "GL-1000"),
        }
        _ERP_INVOICES[iid] = record
        return {"mode": self._mode(), "invoice": record}

    def op_get_stock(self, payload: dict) -> dict:
        sku = payload.get("sku", "SKU-0001")
        return {"mode": self._mode(), "sku": sku,
                "on_hand": 42, "reorder_level": 10, "warehouse": "KHI-01"}

    def op_cost_centres(self, payload: dict) -> dict:
        return {"mode": self._mode(), "cost_centres": [
            {"code": "GL-1000", "name": "Operations"},
            {"code": "GL-2000", "name": "Technology"},
            {"code": "GL-3000", "name": "Marketing"},
        ]}

    def _mode(self) -> str:
        return "live" if self.configured else "sandbox"


# ----------------------------------------------------------- Google Workspace
class GoogleWorkspaceAdapter(BaseAdapter):
    kind = IntegrationKind.GOOGLE_WORKSPACE
    name = "Google Workspace"

    @property
    def configured(self) -> bool:
        import os
        path = settings.GOOGLE_WORKSPACE_CREDENTIALS
        return bool(path and os.path.exists(path))

    def capabilities(self) -> list[str]:
        return ["list_messages", "send_message", "list_events", "append_sheet_row"]

    def health(self) -> dict[str, Any]:
        return {"ok": True, "mode": "live" if self.configured else "sandbox"}

    def op_list_messages(self, payload: dict) -> dict:
        return {"mode": self._mode(), "messages": [
            {"id": "msg-1", "from": "vendor@example.com",
             "subject": "Invoice INV-2026-0847", "has_attachment": True,
             "received_at": _now()},
            {"id": "msg-2", "from": "hr@example.com",
             "subject": "Leave approval request", "has_attachment": False,
             "received_at": _now()},
        ]}

    def op_send_message(self, payload: dict) -> dict:
        if not payload.get("to"):
            raise IntegrationError("send_message requires 'to'")
        return {"mode": self._mode(), "sent": True,
                "to": payload["to"], "subject": payload.get("subject", ""),
                "queued_at": _now()}

    def op_list_events(self, payload: dict) -> dict:
        start = datetime.now(timezone.utc) + timedelta(days=1)
        return {"mode": self._mode(), "events": [
            {"id": "evt-1", "summary": "Finance approval review",
             "start": start.isoformat()},
        ]}

    def op_append_sheet_row(self, payload: dict) -> dict:
        values = payload.get("values")
        if not values:
            raise IntegrationError("append_sheet_row requires 'values'")
        return {"mode": self._mode(), "appended": True,
                "row": values, "sheet": payload.get("sheet", "Sheet1")}

    def _mode(self) -> str:
        return "live" if self.configured else "sandbox"


# ------------------------------------------------------------- Microsoft 365
class Microsoft365Adapter(BaseAdapter):
    kind = IntegrationKind.MICROSOFT_365
    name = "Microsoft 365"

    @property
    def configured(self) -> bool:
        return bool(
            settings.MS365_CLIENT_ID
            and settings.MS365_CLIENT_SECRET
            and settings.MS365_TENANT_ID
        )

    def capabilities(self) -> list[str]:
        return ["list_mail", "send_mail", "list_teams_channels", "post_teams_message"]

    def health(self) -> dict[str, Any]:
        return {"ok": True, "mode": "live" if self.configured else "sandbox"}

    def op_list_mail(self, payload: dict) -> dict:
        return {"mode": self._mode(), "messages": [
            {"id": "ms-1", "from": "procurement@example.com",
             "subject": "PO-NG-2026-112 confirmation", "received_at": _now()},
        ]}

    def op_send_mail(self, payload: dict) -> dict:
        if not payload.get("to"):
            raise IntegrationError("send_mail requires 'to'")
        return {"mode": self._mode(), "sent": True, "to": payload["to"]}

    def op_list_teams_channels(self, payload: dict) -> dict:
        return {"mode": self._mode(), "channels": [
            {"id": "ch-1", "name": "Finance"},
            {"id": "ch-2", "name": "Operations"},
        ]}

    def op_post_teams_message(self, payload: dict) -> dict:
        if not payload.get("channel"):
            raise IntegrationError("post_teams_message requires 'channel'")
        return {"mode": self._mode(), "posted": True,
                "channel": payload["channel"], "at": _now()}

    def _mode(self) -> str:
        return "live" if self.configured else "sandbox"


# -------------------------------------------------------------------- registry
_REGISTRY: dict[str, BaseAdapter] = {
    "crm": CRMAdapter(),
    "erp": ERPAdapter(),
    "google_workspace": GoogleWorkspaceAdapter(),
    "microsoft_365": Microsoft365Adapter(),
}


def get_adapter(key: str) -> BaseAdapter:
    adapter = _REGISTRY.get(key.lower())
    if adapter is None:
        raise IntegrationError(
            f"unknown integration '{key}'. Available: {', '.join(_REGISTRY)}"
        )
    return adapter


def all_adapters() -> list[BaseAdapter]:
    return list(_REGISTRY.values())
