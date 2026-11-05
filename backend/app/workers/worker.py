"""ARQ background worker.

Phase 1 performs resume parsing and scoring inline so the student sees a result in
one request. The worker owns scheduled housekeeping: expired refresh tokens and
interviews that were abandoned with no activity. It is deliberately idempotent so a
retry after a Redis blip is safe.

Run locally:  arq app.workers.worker.WorkerSettings
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import update

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.auth import RefreshToken
from app.models.enums import InterviewStatus
from app.models.interview import Interview

logger = logging.getLogger(__name__)


def _purge_expired_refresh_tokens() -> int:
    cutoff = datetime.now(UTC)
    with SessionLocal() as db:
        result = db.execute(
            update(RefreshToken).where(RefreshToken.expires_at < cutoff).values(revoked=True)
        )
        db.commit()
        return int(result.rowcount or 0)


def _close_stale_interviews(hours: int = 24) -> int:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    with SessionLocal() as db:
        result = db.execute(
            update(Interview)
            .where(
                Interview.status == InterviewStatus.ACTIVE.value,
                Interview.started_at < cutoff,
            )
            .values(status=InterviewStatus.ABANDONED.value)
        )
        db.commit()
        return int(result.rowcount or 0)


async def cleanup_expired_tokens(ctx: dict[str, Any]) -> int:
    """Mark refresh tokens past their expiry as revoked (cron, daily)."""
    purged = await asyncio.to_thread(_purge_expired_refresh_tokens)
    logger.info("worker.refresh_tokens_purged", extra={"count": purged})
    return purged


async def close_stale_interviews(ctx: dict[str, Any]) -> int:
    """Abandon interview rooms with no activity for 24 hours."""
    closed = await asyncio.to_thread(_close_stale_interviews)
    logger.info("worker.stale_interviews_closed", extra={"count": closed})
    return closed


class WorkerSettings:
    functions = [cleanup_expired_tokens, close_stale_interviews]
    cron_jobs = [
        cron(cleanup_expired_tokens, hour=2, minute=30),
        cron(close_stale_interviews, hour=3, minute=0),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
