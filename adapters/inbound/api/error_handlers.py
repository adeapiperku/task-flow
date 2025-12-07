# adapters/inbound/api/error_handlers.py
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from domain.exceptions import AppError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        """
        Global handler for all AppError subclasses.

        This covers:
        - NotFoundError
        - ConflictError
        - ValidationError
        - RepositoryError
        - JobAlreadyExistsError
        - Any other AppError subclass
        """
        payload = {
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=payload,
        )
