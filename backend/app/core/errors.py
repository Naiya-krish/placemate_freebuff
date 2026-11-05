"""Domain errors mapped to stable API responses."""

from __future__ import annotations

from fastapi import HTTPException, status


class ApiError(HTTPException):
    def __init__(self, status_code: int, detail: str, code: str) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.code = code


class NotFoundError(ApiError):
    def __init__(self, detail: str = "Not found") -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, detail, "not_found")


class ForbiddenError(ApiError):
    def __init__(self, detail: str = "Not allowed") -> None:
        super().__init__(status.HTTP_403_FORBIDDEN, detail, "forbidden")


class UploadError(ApiError):
    def __init__(self, detail: str, code: str = "invalid_upload") -> None:
        super().__init__(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail, code)


class BudgetExceededError(ApiError):
    def __init__(self, detail: str = "Monthly AI budget exhausted") -> None:
        super().__init__(status.HTTP_402_PAYMENT_REQUIRED, detail, "budget_exhausted")


class AIOutputError(ApiError):
    def __init__(self, detail: str = "AI returned an invalid response") -> None:
        super().__init__(status.HTTP_502_BAD_GATEWAY, detail, "ai_invalid_output")
