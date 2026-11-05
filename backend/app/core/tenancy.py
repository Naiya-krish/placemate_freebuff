"""Tenant-scoped data access. Every tenant read/write must go through this."""

from __future__ import annotations

import uuid
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError

T = TypeVar("T")


class TenantRepository:
    """Repository that always filters by the caller's college id.

    This is the data-layer enforcement point for multi-tenancy. Route handlers
    never build unscoped queries for tenant-owned models.
    """

    def __init__(self, db: Session, college_id: uuid.UUID) -> None:
        self.db = db
        self.college_id = college_id

    def query(self, model: type[Any]) -> Any:
        if not hasattr(model, "college_id"):
            raise TypeError(f"{model.__name__} is not tenant-scoped")
        return self.db.query(model).filter(model.college_id == self.college_id)

    def get(self, model: type[Any], obj_id: uuid.UUID) -> Any | None:
        return self.query(model).filter(model.id == obj_id).one_or_none()

    def get_or_404(self, model: type[Any], obj_id: uuid.UUID, detail: str = "Not found") -> Any:
        obj = self.get(model, obj_id)
        if obj is None:
            # Deliberately 404 (not 403) so cross-tenant probes cannot confirm existence.
            raise NotFoundError(detail)
        return obj

    def add(self, obj: Any) -> Any:
        if getattr(obj, "college_id", None) != self.college_id:
            raise ValueError("refusing to write an object outside the tenant scope")
        self.db.add(obj)
        return obj

    def count(self, model: type[Any]) -> int:
        return self.query(model).count()
