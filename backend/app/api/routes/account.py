"""DPDP-aligned account deletion."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.deps import CurrentUser, DbSession
from app.core.errors import ApiError
from app.core.security import verify_password
from app.models.resume import Resume
from app.schemas.auth import DeleteAccountRequest
from app.services.storage import get_storage

router = APIRouter(prefix="/account", tags=["account"])


@router.delete("", status_code=204)
def delete_account(
    payload: DeleteAccountRequest,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    if payload.confirm != "DELETE":
        raise ApiError(422, "Type DELETE to confirm", "confirm_required")
    if user.hashed_password and (
        not payload.password or not verify_password(payload.password, user.hashed_password)
    ):
        raise ApiError(401, "Password is required to delete this account", "invalid_credentials")

    resumes = (
        db.query(Resume)
        .filter(Resume.user_id == user.id, Resume.college_id == user.college_id)
        .all()
    )
    storage = get_storage()
    for resume in resumes:
        try:
            storage.delete(resume.storage_key)
        except Exception:
            pass

    # Cascading foreign keys remove resumes, analyses, interviews, turns, scores,
    # usage rows, consents and refresh tokens.
    db.delete(user)
    db.commit()
    response = Response(status_code=204)
    response.delete_cookie("placemate_refresh", path="/api/v1/auth")
    return response
