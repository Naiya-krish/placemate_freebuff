"""Structured JSON logging with PII redaction."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings


class PIIRedactionFilter(logging.Filter):
    """Best-effort scrubbing of emails, phones, bearer tokens and long free text."""

    EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    PHONE = re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)")
    BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+")
    JWT = re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}")
    SECRET_KV = re.compile(r"(?i)(password|secret|token|api_key)\s*[=:]\s*\S+")

    def redact(self, message: str) -> str:
        message = self.BEARER.sub("Bearer [redacted]", message)
        message = self.JWT.sub("[redacted-jwt]", message)
        message = self.EMAIL.sub("[redacted-email]", message)
        message = self.PHONE.sub("[redacted-phone]", message)
        message = self.SECRET_KV.sub(r"\1=[redacted]", message)
        return message

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = self.redact(str(record.getMessage()))
            record.args = ()
            if record.exc_text:
                record.exc_text = self.redact(record.exc_text)
        except Exception:  # pragma: no cover - never break logging
            pass
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "user_id", "college_id", "path", "method", "status_code"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = str(value)
        if record.exc_info and record.exc_text:
            payload["exc"] = record.exc_text
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(PIIRedactionFilter())
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
    for noisy in ("uvicorn.access", "botocore", "boto3", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
