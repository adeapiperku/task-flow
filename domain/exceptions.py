# domain/exceptions.py
from __future__ import annotations

from typing import Any, Optional


class AppError(Exception):
    """
    Base application error with HTTP semantics.

    All domain / app errors should inherit from this.
    """

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: Optional[str] = None, *, details: Any = None):
        super().__init__(message or self.default_message())
        self.message = message or self.default_message()
        self.details = details

    def default_message(self) -> str:
        return "An unexpected error occurred."


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"

    def default_message(self) -> str:
        return "Resource not found."


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"

    def default_message(self) -> str:
        return "Resource conflict."


class ValidationError(AppError):
    status_code = 422
    error_code = "validation_error"

    def default_message(self) -> str:
        return "Request validation failed."


class RepositoryError(AppError):
    status_code = 500
    error_code = "repository_error"

    def default_message(self) -> str:
        return "Persistence error."


class JobAlreadyExistsError(ConflictError):
    error_code = "job_already_exists"

    def default_message(self) -> str:
        return "Job already exists."
