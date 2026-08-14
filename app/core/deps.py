"""Shared FastAPI dependencies: current user, role gates, audit helper."""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_token
from app.database import get_db
from app.models import AuditLog, Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    payload = decode_token(token, expected_type="access")
    if payload is None:
        raise CREDENTIALS_ERROR

    subject = payload.get("sub")
    if not subject:
        raise CREDENTIALS_ERROR

    user = db.query(User).filter(User.id == int(subject)).first()
    if user is None:
        raise CREDENTIALS_ERROR
    if not user.is_active:
        # Deactivating a user takes effect immediately, even while they hold a
        # token that has not yet expired.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )
    return user


def require_role(minimum: Role):
    """Dependency factory gating a route on a minimum role.

    Roles are hierarchical, so `require_role(Role.MANAGER)` also admits admins.
    """

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not user.role.can_act_as(minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"This action requires the {minimum.value} role or higher; "
                    f"your role is {user.role.value}"
                ),
            )
        return user

    return dependency


require_admin = require_role(Role.ADMIN)
require_manager = require_role(Role.MANAGER)
require_analyst = require_role(Role.ANALYST)
require_viewer = require_role(Role.VIEWER)


def record_audit(
    db: Session,
    action: str,
    actor: User | None = None,
    entity_type: str = "",
    entity_id: int | None = None,
    detail: dict | None = None,
    request: Request | None = None,
) -> AuditLog:
    """Append an audit entry. Commits, so callers need not remember to."""
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail or {},
        ip_address=(request.client.host if request and request.client else ""),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
