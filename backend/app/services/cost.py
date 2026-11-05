"""Per-user token/cost ledger and monthly budget enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BudgetExceededError
from app.models.usage import UsageEvent
from app.models.user import User
from app.schemas.dashboard import UsageSummary

# USD per 1M tokens (input, output). Unknown models use a conservative default.
PRICING: dict[str, tuple[float, float]] = {
    "mock": (0.0, 0.0),
    "gemini-2.0-flash-001": (0.10, 0.40),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-1.5-pro": (1.25, 5.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def current_month(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m")


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    if model.startswith("mock"):
        return 0.0
    rate = next((v for k, v in PRICING.items() if model.startswith(k)), (0.50, 1.50))
    return round((input_tokens / 1_000_000) * rate[0] + (output_tokens / 1_000_000) * rate[1], 6)


def monthly_spend(db: Session, user_id: object, month: str | None = None) -> float:
    month = month or current_month()
    total = (
        db.query(func.coalesce(func.sum(UsageEvent.cost_usd), 0.0))
        .filter(UsageEvent.user_id == user_id, UsageEvent.month == month)
        .scalar()
    )
    return float(total or 0.0)


def assert_budget(db: Session, user: User) -> None:
    spent = monthly_spend(db, user.id)
    if spent >= settings.per_user_monthly_budget:
        raise BudgetExceededError(
            f"Monthly AI budget of ${settings.per_user_monthly_budget:.2f} is exhausted. "
            "It resets on the 1st of next month."
        )


def record_usage(
    db: Session,
    user: User,
    *,
    feature: str,
    result: Any,
    prompt_version: str | None = None,
) -> UsageEvent:
    event = UsageEvent(
        college_id=user.college_id,
        user_id=user.id,
        feature=feature,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=estimate_cost(result.model, result.input_tokens, result.output_tokens),
        month=current_month(),
    )
    db.add(event)
    # Log the prompt version in the feature label trail (kept short, no PII).
    db.flush()
    return event


def usage_summary(db: Session, user: User) -> UsageSummary:
    month = current_month()
    rows = (
        db.query(UsageEvent).filter(UsageEvent.user_id == user.id, UsageEvent.month == month).all()
    )
    cost = sum(r.cost_usd for r in rows)
    tokens = sum(r.input_tokens + r.output_tokens for r in rows)
    budget = settings.per_user_monthly_budget
    return UsageSummary(
        month=month,
        tokens=tokens,
        cost_usd=round(cost, 4),
        budget_usd=budget,
        remaining_usd=round(max(0.0, budget - cost), 4),
        percent_used=min(100, int((cost / budget) * 100)) if budget else 0,
    )
