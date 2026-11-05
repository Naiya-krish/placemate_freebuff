"""Authentication: email/password, Google OAuth, refresh rotation, consent."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Header, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import func

from app.api.deps import CurrentUser, DbSession, assert_same_origin
from app.core.config import settings
from app.core.errors import ApiError, ForbiddenError, NotFoundError
from app.core.ratelimit import limiter
from app.core.security import (
    ALGORITHM,
    create_access_token,
    hash_password,
    new_refresh_token,
    verify_password,
)
from app.models.auth import Consent, RefreshToken
from app.models.enums import Role
from app.models.user import College, User
from app.schemas.auth import (
    ConsentUpdate,
    LoginRequest,
    OnboardingUpdate,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.defaults import ensure_default_rubric

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "placemate_refresh"
COOKIE_PATH = "/api/v1/auth"


def _college_by_code(db: DbSession, code: str) -> College:
    college = (
        db.query(College)
        .filter(func.upper(College.code) == code.strip().upper(), College.is_active.is_(True))
        .one_or_none()
    )
    if college is None:
        raise NotFoundError("No active college matches that code")
    return college


def _user_out(user: User, db: DbSession) -> UserOut:
    college = db.get(College, user.college_id)
    data = UserOut.model_validate(user)
    data.college_name = college.name if college else None
    return data


def _set_refresh_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.api_public_url.startswith("https"),
        samesite="strict",
        path=COOKIE_PATH,
    )


def _issue_tokens(db: DbSession, user: User, response: Response) -> TokenResponse:
    access, expires_in = create_access_token(
        user_id=user.id, college_id=user.college_id, role=user.role
    )
    raw, hashed = new_refresh_token()
    db.add(
        RefreshToken(
            college_id=user.college_id,
            user_id=user.id,
            token_hash=hashed,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    db.commit()
    _set_refresh_cookie(response, raw)
    return TokenResponse(access_token=access, expires_in=expires_in, user=_user_out(user, db))


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit(settings.rate_limit_auth)
def register(
    request: Request, payload: RegisterRequest, db: DbSession, response: Response
) -> TokenResponse:
    if not payload.consent_notice:
        raise ApiError(
            422, "Please accept the privacy notice to create an account", "consent_required"
        )
    college = _college_by_code(db, payload.college_code)
    existing = (
        db.query(User)
        .filter(User.college_id == college.id, func.lower(User.email) == payload.email.lower())
        .one_or_none()
    )
    if existing is not None:
        raise ApiError(
            409, "An account already exists for this email at your college", "email_exists"
        )

    user = User(
        college_id=college.id,
        email=payload.email.lower(),
        name=payload.name.strip(),
        hashed_password=hash_password(payload.password),
        role=Role.STUDENT.value,
        branch=payload.branch.strip(),
        target_role=payload.target_role.strip(),
        consent_share_analytics=payload.share_analytics,
        consent_policy_version=settings.policy_version,
        onboarding_complete=False,
    )
    db.add(user)
    db.flush()
    db.add(
        Consent(
            college_id=college.id,
            user_id=user.id,
            purpose="privacy_notice",
            granted=True,
            policy_version=settings.policy_version,
        )
    )
    db.add(
        Consent(
            college_id=college.id,
            user_id=user.id,
            purpose="analytics_sharing",
            granted=payload.share_analytics,
            policy_version=settings.policy_version,
        )
    )
    ensure_default_rubric(db, college.id)
    db.commit()
    return _issue_tokens(db, user, response)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_auth)
def login(
    request: Request, payload: LoginRequest, db: DbSession, response: Response
) -> TokenResponse:
    query = db.query(User).filter(func.lower(User.email) == payload.email.lower())
    if payload.college_code:
        college = _college_by_code(db, payload.college_code)
        query = query.filter(User.college_id == college.id)
    users = query.all()
    if len(users) > 1:
        raise ApiError(
            409, "This email exists at multiple colleges; add your college code", "college_required"
        )
    user = users[0] if users else None
    if (
        user is None
        or not user.is_active
        or not user.hashed_password
        or not verify_password(payload.password, user.hashed_password)
    ):
        # identical response for unknown user and bad password
        raise ApiError(401, "Incorrect email or password", "invalid_credentials")
    college_row = db.get(College, user.college_id)
    if college_row is None or not college_row.is_active:
        raise ForbiddenError("This college account is inactive")
    return _issue_tokens(db, user, response)


@router.post("/demo-login", response_model=TokenResponse)
@limiter.limit(settings.rate_limit_auth)
def demo_login(
    request: Request, response: Response, db: DbSession, role: str = "student"
) -> TokenResponse:
    if not settings.demo_mode:
        raise NotFoundError()
    if role not in {"student", "officer", "admin"}:
        raise ApiError(422, "role must be student, officer or admin", "invalid_role")
    user = (
        db.query(User)
        .filter(User.email == f"{role}@placemate.dev")
        .order_by(User.created_at.asc())
        .first()
    )
    if user is None:
        raise NotFoundError("Demo data has not been seeded")
    return _issue_tokens(db, user, response)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    db: DbSession,
    origin: str | None = Header(default=None),
) -> TokenResponse:
    assert_same_origin(request, origin)
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise ApiError(401, "Missing refresh token", "no_refresh_token")
    from app.core.security import hash_refresh_token

    row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_refresh_token(raw), RefreshToken.revoked.is_(False))
        .one_or_none()
    )
    expires = row.expires_at if row else None
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if row is None or expires is None or expires < datetime.now(UTC):
        raise ApiError(401, "Refresh token is invalid or expired", "invalid_refresh_token")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise ForbiddenError("Account is not active")
    row.revoked = True
    db.commit()
    return _issue_tokens(db, user, response)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DbSession) -> Response:
    raw = request.cookies.get(REFRESH_COOKIE)
    if raw:
        from app.core.security import hash_refresh_token

        db.query(RefreshToken).filter(RefreshToken.token_hash == hash_refresh_token(raw)).update(
            {"revoked": True}
        )
        db.commit()
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser, db: DbSession) -> UserOut:
    return _user_out(user, db)


@router.patch("/onboarding", response_model=UserOut)
def complete_onboarding(payload: OnboardingUpdate, user: CurrentUser, db: DbSession) -> UserOut:
    if user.role != Role.STUDENT.value:
        raise ForbiddenError("Onboarding is for student accounts")
    user.branch = payload.branch.strip()
    user.target_role = payload.target_role.strip()
    user.onboarding_complete = payload.complete
    db.commit()
    return _user_out(user, db)


@router.post("/consent", response_model=UserOut)
def update_consent(payload: ConsentUpdate, user: CurrentUser, db: DbSession) -> UserOut:
    policy = payload.policy_version or settings.policy_version
    user.consent_share_analytics = payload.share_analytics
    user.consent_policy_version = policy
    db.add(
        Consent(
            college_id=user.college_id,
            user_id=user.id,
            purpose="analytics_sharing",
            granted=payload.share_analytics,
            policy_version=policy,
        )
    )
    db.commit()
    return _user_out(user, db)


def _oauth_state(college_code: str) -> str:
    return jwt.encode(
        {
            "type": "oauth",
            "college_code": college_code.upper(),
            "nonce": secrets.token_urlsafe(12),
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        },
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )


@router.get("/google/login")
def google_login(college_code: str = "NOVA") -> RedirectResponse:
    if not settings.auth_google_client_id or not settings.auth_google_client_secret:
        raise ApiError(
            503,
            "Google login is not configured. Use email/password or demo login.",
            "google_not_configured",
        )
    redirect_uri = f"{settings.api_public_url.rstrip('/')}/api/v1/auth/google/callback"
    params = {
        "client_id": settings.auth_google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": _oauth_state(college_code),
        "prompt": "select_account",
    }
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(request: Request, db: DbSession, code: str, state: str) -> RedirectResponse:
    if not settings.auth_google_client_id or not settings.auth_google_client_secret:
        raise ApiError(503, "Google login is not configured", "google_not_configured")
    try:
        state_payload = jwt.decode(state, settings.jwt_secret, algorithms=[ALGORITHM])
        if state_payload.get("type") != "oauth":
            raise jwt.InvalidTokenError("wrong state type")
        college = _college_by_code(db, str(state_payload["college_code"]))
    except (jwt.PyJWTError, KeyError) as exc:
        raise ApiError(400, "Invalid OAuth state; please try again", "invalid_state") from exc
    redirect_uri = f"{settings.api_public_url.rstrip('/')}/api/v1/auth/google/callback"
    try:
        token_response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.auth_google_client_id,
                "client_secret": settings.auth_google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=20,
        )
        token_response.raise_for_status()
        id_token_value = token_response.json().get("id_token")
        if not id_token_value:
            raise ApiError(400, "Google did not return an identity token", "oauth_failed")
        claims: dict[str, Any] = jwt.decode(id_token_value, options={"verify_signature": False})
        email = str(claims.get("email", "")).lower()
        if not email or not claims.get("email_verified"):
            raise ApiError(400, "Google account email is not verified", "oauth_failed")
    except httpx.HTTPError as exc:
        raise ApiError(400, "Google sign-in failed; try email login", "oauth_failed") from exc

    user = (
        db.query(User)
        .filter(User.college_id == college.id, func.lower(User.email) == email)
        .one_or_none()
    )
    if user is None:
        user = User(
            college_id=college.id,
            email=email,
            name=str(claims.get("name", email.split("@")[0]))[:160],
            google_sub=str(claims.get("sub"))[:120] if claims.get("sub") else None,
            avatar_url=str(claims.get("picture"))[:500] if claims.get("picture") else None,
            role=Role.STUDENT.value,
            consent_share_analytics=False,
        )
        db.add(user)
        db.commit()
        ensure_default_rubric(db, college.id)
    elif user.google_sub is None and claims.get("sub"):
        user.google_sub = str(claims["sub"])[:120]
        db.commit()
    if not user.is_active:
        raise ForbiddenError("Account is not active")

    raw, hashed = new_refresh_token()
    db.add(
        RefreshToken(
            college_id=user.college_id,
            user_id=user.id,
            token_hash=hashed,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    db.commit()
    redirect = RedirectResponse(f"{settings.frontend_url.rstrip('/')}/auth/callback")
    _set_refresh_cookie(redirect, raw)
    return redirect


@router.get("/colleges", response_model=list[dict[str, str]])
def public_colleges(db: DbSession) -> list[dict[str, str]]:
    rows = (
        db.query(College)
        .filter(College.is_active.is_(True))
        .order_by(College.name.asc())
        .limit(50)
        .all()
    )
    return [{"code": c.code, "name": c.name} for c in rows]
