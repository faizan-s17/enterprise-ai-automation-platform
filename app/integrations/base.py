"""Adapter contract shared by every external business system.

Each adapter reports whether it is running live or in sandbox. Sandbox mode is
deliberate rather than a stub left behind: connecting real Salesforce, SAP,
Google Workspace and Microsoft 365 tenants needs four paid enterprise accounts,
so the platform ships with in-memory implementations that honour the same
interface. Supplying credentials switches an adapter to live with no code
change, and `/integrations` reports which mode each one is in so a live demo
never misrepresents itself.
"""
from __future__ import annotations

import abc
from typing import Any

from app.models import IntegrationKind, IntegrationStatus


class IntegrationError(RuntimeError):
    pass


class BaseAdapter(abc.ABC):
    kind: IntegrationKind
    name: str

    @property
    @abc.abstractmethod
    def configured(self) -> bool:
        """True when real credentials are present."""

    @property
    def status(self) -> IntegrationStatus:
        return (
            IntegrationStatus.CONNECTED if self.configured
            else IntegrationStatus.SANDBOX
        )

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind.value,
            "status": self.status.value,
            "mode": "live" if self.configured else "sandbox",
            "capabilities": self.capabilities(),
        }

    @abc.abstractmethod
    def capabilities(self) -> list[str]:
        """Operation names this adapter supports."""

    @abc.abstractmethod
    def health(self) -> dict[str, Any]:
        """Cheap reachability check."""

    def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch to `op_<operation>`."""
        handler = getattr(self, f"op_{operation}", None)
        if handler is None:
            raise IntegrationError(
                f"{self.name} does not support '{operation}'. "
                f"Available: {', '.join(self.capabilities())}"
            )
        return handler(payload)
