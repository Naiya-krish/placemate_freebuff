from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import EmbeddingType, JSONType
from app.models.enums import Role


class QuestionBank(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # NULL = global/shared bank managed by platform admins
    college_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("colleges.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(40), default="swe", nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(40), default="project", nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    ideal_answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    key_points: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType(768), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_role: Mapped[str] = mapped_column(String(20), default=Role.ADMIN.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
