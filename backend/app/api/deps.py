from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated, Any

import jwt
from fastapi import Depends, Header, Request, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError
from app.core.security import decode_access_token
from app.core.tenancy import TenantRepository
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import College, User

bearer = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def _load_user(db: Session, payload: dict[str, Any]) -> User:
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise ForbiddenError("Account is not active")
    if str(user.college_id) != payload.get("college_id"):
        raise ForbiddenError("Tenant mismatch")
    college = db.get(College, user.college_id)
    if college is None or not college.is_active:
        raise ForbiddenError("College is not active")
    return user


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: DbSession,
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return _load_user(db, payload)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[..., Any]:
    def dependency(user: CurrentUser) -> User:
        if user.role not in {r.value for r in roles}:
            raise ForbiddenError("This area requires a different role")
        return user

    return dependency


def get_repo(user: CurrentUser, db: DbSession) -> TenantRepository:
    return TenantRepository(db, user.college_id)


Repo = Annotated[TenantRepository, Depends(get_repo)]


def assert_same_origin(request: Request, origin: str | None = Header(default=None)) -> None:
    """CSRF guard for cookie-authenticated endpoints."""
    from app.core.config import settings

    if origin is None:
        return
    if origin.rstrip("/") not in {o.rstrip("/") for o in settings.allowed_origins}:
        raise ForbiddenError("Origin is not allowed")


def user_from_ws(websocket: WebSocket, db: Session) -> User:
    token = websocket.query_params.get("token")
    header = websocket.headers.get("authorization", "")
    if not token and header.lower().startswith("bearer "):
        token = header[7:]
    if not token:
        raise ForbiddenError("Missing interview token")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise ForbiddenError("Invalid interview token") from exc
    return _load_user(db, payload)


def get_college(db: Session, user: User) -> College:
    college = db.get(College, user.college_id)
    if college is None:
        raise NotFoundError("College not found")
    return college
