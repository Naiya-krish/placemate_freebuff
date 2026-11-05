"""Interviews: REST lifecycle, rubric visibility and the full-duplex WebSocket room."""

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUser, DbSession, Repo, user_from_ws
from app.core.config import settings
from app.core.errors import ApiError, ForbiddenError, NotFoundError
from app.core.ratelimit import limiter
from app.db.session import SessionLocal
from app.models.enums import InterviewStatus, Role, Round
from app.models.interview import Interview, InterviewTurn
from app.models.resume import Resume
from app.models.rubric import RubricVersion
from app.models.user import User
from app.schemas.interview import (
    FeedbackOut,
    InterviewCreate,
    InterviewDetail,
    InterviewOut,
    RubricOut,
    ScoreCriterionOut,
    TurnOut,
)
from app.services import gamification
from app.services.defaults import active_rubric, ensure_default_rubric
from app.services.interview_service import (
    create_interview,
    finish_interview,
    get_owned_interview,
    hint_for,
    start_interview,
    submit_answer,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["interviews"])


def _rubric(db: DbSession, user: User) -> RubricVersion:
    return ensure_default_rubric(db, user.college_id)


@router.get("/rubrics/active", response_model=RubricOut)
def get_active_rubric(user: CurrentUser, db: DbSession) -> RubricOut:
    rubric = _rubric(db, user)
    return RubricOut(
        version=rubric.version,
        label=rubric.label,
        criteria=rubric.criteria,  # type: ignore[arg-type]
    )


@router.post("/interviews", response_model=InterviewOut, status_code=201)
@limiter.limit(settings.rate_limit_interview)
def create(
    request: Request, payload: InterviewCreate, user: CurrentUser, db: DbSession, repo: Repo
) -> Interview:
    if user.role != Role.STUDENT.value:
        raise ForbiddenError("Only students can take interviews")
    resume = repo.get_or_404(Resume, payload.resume_id, "Resume not found")
    if resume.user_id != user.id:
        raise NotFoundError("Resume not found")
    interview = create_interview(
        db,
        user,
        resume=resume,
        role=(payload.role or "auto"),
        target_role=payload.target_role,
    )
    db.commit()
    db.refresh(interview)
    return interview


@router.get("/interviews", response_model=list[InterviewOut])
def list_interviews(user: CurrentUser, db: DbSession, repo: Repo) -> list[Interview]:
    if user.role != Role.STUDENT.value:
        return []
    return (
        repo.query(Interview)
        .filter(Interview.user_id == user.id)
        .order_by(Interview.started_at.desc())
        .all()
    )


@router.get("/interviews/{interview_id}", response_model=InterviewDetail)
def get_interview(interview_id: uuid.UUID, user: CurrentUser, db: DbSession) -> InterviewDetail:
    interview = get_owned_interview(db, user, interview_id)
    turns = (
        db.query(InterviewTurn)
        .filter(InterviewTurn.interview_id == interview.id)
        .order_by(InterviewTurn.idx.asc())
        .all()
    )
    base = InterviewOut.model_validate(interview)
    return InterviewDetail(
        **base.model_dump(),
        rubric_scores=interview.rubric_scores,
        feedback=interview.feedback,
        turns=[TurnOut.model_validate(t) for t in turns],
    )


@router.post("/interviews/{interview_id}/finish", response_model=FeedbackOut)
def finish(interview_id: uuid.UUID, user: CurrentUser, db: DbSession) -> FeedbackOut:
    interview = get_owned_interview(db, user, interview_id)
    if interview.status != InterviewStatus.ACTIVE.value:
        raise ApiError(409, "Interview is already scored", "already_scored")
    rubric = (
        db.query(RubricVersion)
        .filter(
            RubricVersion.college_id == user.college_id,
            RubricVersion.version == interview.rubric_version,
        )
        .one_or_none()
    ) or active_rubric(db, user.college_id)
    finish_interview(db, user, interview, rubric)
    db.commit()
    db.refresh(interview)
    turns = (
        db.query(InterviewTurn)
        .filter(InterviewTurn.interview_id == interview.id)
        .order_by(InterviewTurn.idx.asc())
        .all()
    )
    return _feedback(interview, turns)


@router.get("/interviews/{interview_id}/feedback", response_model=FeedbackOut)
def feedback(interview_id: uuid.UUID, user: CurrentUser, db: DbSession) -> FeedbackOut:
    interview = get_owned_interview(db, user, interview_id)
    if interview.status != InterviewStatus.COMPLETED.value or interview.overall_score is None:
        raise ApiError(409, "Finish the interview to see rubric feedback", "not_scored")
    turns = (
        db.query(InterviewTurn)
        .filter(InterviewTurn.interview_id == interview.id)
        .order_by(InterviewTurn.idx.asc())
        .all()
    )
    return _feedback(interview, turns)


def _feedback(interview: Interview, turns: list[InterviewTurn]) -> FeedbackOut:
    criteria = []
    for item in interview.rubric_scores or []:
        criteria.append(
            ScoreCriterionOut(
                key=str(item.get("key", "")),
                label=str(item.get("label", item.get("key", ""))),
                weight=float(item.get("weight", 0)),
                score=int(item.get("score", 0)),
                note=str(item.get("note", "")),
                improvement=str(item.get("improvement", "")),
            )
        )
    return FeedbackOut(
        interview_id=interview.id,
        overall_score=interview.overall_score,
        rubric_version=interview.rubric_version,
        criteria=criteria,
        feedback=interview.feedback,
        transcript=[TurnOut.model_validate(t) for t in turns],
        variance_flag=interview.variance_flag,
    )


def _score_payload(result: dict[str, Any], interview: Interview) -> dict[str, Any]:
    return {
        "type": "scored",
        "interview_id": str(interview.id),
        "overall": result["overall"],
        "criteria": result["criteria"],
        "feedback": result["feedback"],
        "variance_flag": result["variance_flag"],
        "rubric_version": result["rubric_version"],
        "prompt_version": result["prompt_version"],
        "model": result["model"],
    }


@router.websocket("/interviews/{interview_id}/ws")
async def interview_ws(websocket: WebSocket, interview_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        try:
            user = user_from_ws(websocket, db)
            interview = get_owned_interview(db, user, interview_id)
        except Exception:
            await websocket.close(code=4401, reason="Unauthorized")
            return
        if interview.status != InterviewStatus.ACTIVE.value:
            await websocket.accept()
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "interview_complete",
                    "message": "This interview is already scored.",
                }
            )
            await websocket.close(code=1000)
            return

        await websocket.accept()
        turns = (
            db.query(InterviewTurn)
            .filter(InterviewTurn.interview_id == interview.id)
            .order_by(InterviewTurn.idx.asc())
            .all()
        )
        rubric = (
            db.query(RubricVersion)
            .filter(
                RubricVersion.college_id == user.college_id,
                RubricVersion.version == interview.rubric_version,
            )
            .one_or_none()
        )
        await websocket.send_json(
            {
                "type": "session",
                "interview_id": str(interview.id),
                "role": interview.role,
                "round": interview.current_round,
                "rounds": [r.value for r in Round],
                "rubric": {
                    "version": interview.rubric_version,
                    "label": rubric.label if rubric else "Standard rubric",
                    "criteria": rubric.criteria if rubric else [],
                },
                "timer_seconds": interview.duration_seconds,
                "xp": user.xp,
            }
        )
        if turns:
            last_question = next((t for t in reversed(turns) if t.speaker == "interviewer"), None)
            if last_question:
                await websocket.send_json(
                    {
                        "type": "question",
                        "id": str(last_question.id),
                        "round": last_question.round,
                        "text": last_question.content,
                        "is_followup": last_question.is_followup,
                        "resumed": True,
                    }
                )
        else:
            await websocket.send_json({"type": "typing", "on": True})
            question = await run_in_threadpool(start_interview, db, user, interview)
            db.commit()
            await websocket.send_json(
                {
                    "type": "question",
                    "id": str(question.id),
                    "round": question.round,
                    "text": question.content,
                    "is_followup": False,
                }
            )
            await websocket.send_json({"type": "typing", "on": False})

        message_count = 0
        while True:
            raw = await websocket.receive_text()
            if len(raw) > 12_000:
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "message_too_large",
                        "message": "Keep messages under 12 KB.",
                    }
                )
                continue
            message_count += 1
            if message_count > 80:
                await websocket.send_json(
                    {"type": "error", "code": "rate_limited", "message": "Slow down a little."}
                )
                await websocket.close(code=1008)
                return
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "code": "invalid_json", "message": "Expected JSON messages."}
                )
                continue
            kind = str(message.get("type", ""))

            if kind == "ping":
                await websocket.send_json({"type": "pong"})

            elif kind == "hint":
                interview.hint_count += 1
                gamification.award_xp(user, -5)
                db.commit()
                await websocket.send_json(
                    {
                        "type": "hint",
                        "text": hint_for(db, interview),
                        "xp_penalty": 5,
                        "xp": user.xp,
                        "hints_used": interview.hint_count,
                    }
                )

            elif kind == "answer":
                content = str(message.get("content", "")).strip()
                if len(content) < 2:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "code": "answer_too_short",
                            "message": "Give a slightly longer answer.",
                        }
                    )
                    continue
                await websocket.send_json({"type": "typing", "on": True})
                step = await run_in_threadpool(submit_answer, db, user, interview, content)
                db.commit()
                await websocket.send_json({"type": "typing", "on": False})
                if step.round_completed:
                    await websocket.send_json(
                        {
                            "type": "round_complete",
                            "round": step.round_completed,
                            "next": step.next_round,
                            "finished": step.finished,
                        }
                    )
                if step.question is not None:
                    await websocket.send_json(
                        {
                            "type": "question",
                            "id": str(step.question.id),
                            "round": step.question.round,
                            "text": step.question.content,
                            "is_followup": step.question.is_followup,
                        }
                    )

            elif kind == "finish":
                await websocket.send_json({"type": "typing", "on": True})
                active_rubric_row = (
                    db.query(RubricVersion)
                    .filter(
                        RubricVersion.college_id == user.college_id,
                        RubricVersion.version == interview.rubric_version,
                    )
                    .one_or_none()
                ) or active_rubric(db, user.college_id)
                try:
                    result = await run_in_threadpool(
                        finish_interview, db, user, interview, active_rubric_row
                    )
                    db.commit()
                except ApiError as exc:
                    db.rollback()
                    await websocket.send_json(
                        {"type": "error", "code": exc.code, "message": str(exc.detail)}
                    )
                    continue
                await websocket.send_json({"type": "typing", "on": False})
                await websocket.send_json(_score_payload(result, interview))
                await websocket.close(code=1000)
                return

            else:
                await websocket.send_json(
                    {"type": "error", "code": "unknown_type", "message": "Unknown message type."}
                )

    except WebSocketDisconnect:
        db.rollback()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception(
            "interview_ws_failed interview=%s error=%s", interview_id, type(exc).__name__
        )
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "code": "server_error",
                    "message": "The interview room hit an error. Rejoin to continue.",
                }
            )
        except Exception:
            pass
    finally:
        db.close()


# FastAPI's websocket exceptions cannot use the HTTP error handler; REST probes use this.
@router.get("/interviews/{interview_id}/ws", include_in_schema=False)
def ws_probe(interview_id: uuid.UUID) -> JSONResponse:
    return JSONResponse(
        {
            "detail": "This endpoint upgrades to a WebSocket. Connect with a short-lived access token."
        },
        status_code=426,
    )
