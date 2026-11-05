from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import JSONType
from app.models.enums import InterviewStatus, Round


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    college_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"), index=True
    )
    role: Mapped[str] = mapped_column(String(40), default="swe", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=InterviewStatus.ACTIVE.value, nullable=False
    )
    current_round: Mapped[str] = mapped_column(
        String(16), default=Round.PROJECT.value, nullable=False
    )
    current_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    followups_asked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hint_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="mock", nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float)
    rubric_scores: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    feedback: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    variance_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InterviewTurn(Base):
    __tablename__ = "interview_turns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    college_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), index=True, nullable=False
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), index=True, nullable=False
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[str] = mapped_column(String(16), nullable=False)
    speaker: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_followup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hint_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class InterviewScore(Base):
    __tablename__ = "interview_scores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    college_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), index=True, nullable=False
    )
    interview_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    samples: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list, nullable=False)
    medians: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list, nullable=False)
    overall: Mapped[float] = mapped_column(Float, nullable=False)
    spread: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    variance_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(32), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
