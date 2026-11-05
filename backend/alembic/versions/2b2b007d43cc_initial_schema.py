"""initial schema with pgvector question embeddings

Revision ID: 2b2b007d43cc
Revises:
Create Date: 2026-11-02 18:59:12.669628
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "2b2b007d43cc"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
EMBEDDING = sa.JSON().with_variant(Vector(768), "postgresql")
TS = sa.text("(CURRENT_TIMESTAMP)")


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "colleges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("placement_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("colleges", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_colleges_code"), ["code"], unique=True)

    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("topic", sa.String(length=40), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("ideal_answer", sa.Text(), nullable=False),
        sa.Column("key_points", JSON, nullable=False),
        sa.Column("embedding", EMBEDDING, nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("questions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_questions_college_id"), ["college_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_questions_role"), ["role"], unique=False)
        batch_op.create_index(batch_op.f("ix_questions_topic"), ["topic"], unique=False)
    if is_postgres:
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_questions_embedding_hnsw ON questions "
            "USING hnsw (embedding vector_cosine_ops)"
        )

    op.create_table(
        "rubric_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("criteria", JSON, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("rubric_versions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_rubric_versions_college_id"), ["college_id"], unique=False
        )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("google_sub", sa.String(length=120), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("branch", sa.String(length=60), nullable=True),
        sa.Column("target_role", sa.String(length=80), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("streak_count", sa.Integer(), nullable=False),
        sa.Column("last_active_date", sa.Date(), nullable=True),
        sa.Column("consent_share_analytics", sa.Boolean(), nullable=False),
        sa.Column("consent_policy_version", sa.String(length=20), nullable=True),
        sa.Column("onboarding_complete", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("college_id", "email", name="uq_user_college_email"),
        sa.UniqueConstraint("google_sub"),
    )
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_users_college_id"), ["college_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=False)

    op.create_table(
        "consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=60), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("policy_version", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("consents", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_consents_college_id"), ["college_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_consents_user_id"), ["user_id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_refresh_tokens_college_id"), ["college_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_refresh_tokens_token_hash"), ["token_hash"], unique=True
        )
        batch_op.create_index(batch_op.f("ix_refresh_tokens_user_id"), ["user_id"], unique=False)

    op.create_table(
        "resumes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("used_ocr", sa.Boolean(), nullable=False),
        sa.Column("pages", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("parsed_data", JSON, nullable=False),
        sa.Column("warnings", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("resumes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_resumes_college_id"), ["college_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_resumes_sha256"), ["sha256"], unique=False)
        batch_op.create_index(batch_op.f("ix_resumes_user_id"), ["user_id"], unique=False)

    op.create_table(
        "usage_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("feature", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("usage_events", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_usage_events_college_id"), ["college_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_usage_events_month"), ["month"], unique=False)
        batch_op.create_index(batch_op.f("ix_usage_events_user_id"), ["user_id"], unique=False)

    op.create_table(
        "interviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("current_round", sa.String(length=16), nullable=False),
        sa.Column("current_index", sa.Integer(), nullable=False),
        sa.Column("followups_asked", sa.Integer(), nullable=False),
        sa.Column("hint_count", sa.Integer(), nullable=False),
        sa.Column("rubric_version", sa.String(length=32), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("rubric_scores", JSON, nullable=False),
        sa.Column("feedback", JSON, nullable=False),
        sa.Column("variance_flag", sa.Boolean(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("interviews", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_interviews_college_id"), ["college_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_interviews_resume_id"), ["resume_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_interviews_user_id"), ["user_id"], unique=False)

    op.create_table(
        "resume_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("target_role", sa.String(length=80), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("subscores", JSON, nullable=False),
        sa.Column("suggestions", JSON, nullable=False),
        sa.Column("missing_evidence", JSON, nullable=False),
        sa.Column("injection_flags", JSON, nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("resume_analyses", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_resume_analyses_college_id"), ["college_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_resume_analyses_resume_id"), ["resume_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_resume_analyses_user_id"), ["user_id"], unique=False
        )

    op.create_table(
        "interview_scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.Column("samples", JSON, nullable=False),
        sa.Column("medians", JSON, nullable=False),
        sa.Column("overall", sa.Float(), nullable=False),
        sa.Column("spread", sa.Float(), nullable=False),
        sa.Column("variance_flag", sa.Boolean(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("rubric_version", sa.String(length=32), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("interview_id"),
    )
    with op.batch_alter_table("interview_scores", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_interview_scores_college_id"), ["college_id"], unique=False
        )

    op.create_table(
        "interview_turns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("college_id", sa.Uuid(), nullable=False),
        sa.Column("interview_id", sa.Uuid(), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("round", sa.String(length=16), nullable=False),
        sa.Column("speaker", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_followup", sa.Boolean(), nullable=False),
        sa.Column("hint_used", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=TS, nullable=False),
        sa.ForeignKeyConstraint(["college_id"], ["colleges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("interview_turns", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_interview_turns_college_id"), ["college_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_interview_turns_interview_id"), ["interview_id"], unique=False
        )


def downgrade() -> None:
    op.drop_table("interview_turns")
    op.drop_table("interview_scores")
    op.drop_table("resume_analyses")
    op.drop_table("interviews")
    op.drop_table("usage_events")
    op.drop_table("resumes")
    op.drop_table("refresh_tokens")
    op.drop_table("consents")
    op.drop_table("users")
    op.drop_table("rubric_versions")
    op.drop_index("ix_questions_embedding_hnsw", table_name="questions")
    op.drop_table("questions")
    op.drop_table("colleges")
