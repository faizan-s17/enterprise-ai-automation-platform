from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, record_audit, require_analyst
from app.database import get_db
from app.integrations.adapters import all_adapters, get_adapter
from app.integrations.base import IntegrationError
from app.models import User

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("")
def list_integrations(_: User = Depends(get_current_user)):
    """Every connected system and whether it is live or in sandbox."""
    return [a.describe() for a in all_adapters()]


@router.get("/{key}/health")
def integration_health(key: str, _: User = Depends(get_current_user)):
    try:
        adapter = get_adapter(key)
    except IntegrationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"integration": adapter.name, **adapter.health()}


@router.post("/{key}/execute")
def execute_operation(
    key: str,
    request: Request,
    operation: str = Body(..., embed=True),
    payload: dict[str, Any] = Body(default_factory=dict, embed=True),
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    """Run one operation against a connected system.

    A single dispatch endpoint rather than a route per operation, so adding a
    capability to an adapter exposes it through the API immediately.
    """
    try:
        adapter = get_adapter(key)
    except IntegrationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        result = adapter.execute(operation, payload)
    except IntegrationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{adapter.name} call failed: {exc}",
        ) from exc

    record_audit(db, "integration.execute", user, "integration", None,
                 {"integration": key, "operation": operation}, request)
    return {"integration": adapter.name, "operation": operation, "result": result}
