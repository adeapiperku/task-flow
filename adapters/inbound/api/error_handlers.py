"""
Error handlers for the FastAPI application.

This module provides centralized error handling for the API, ensuring consistent
error responses and proper logging.
"""
import logging
import traceback
import uuid
from typing import Any, Dict, Optional, Type, Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.responses import JSONResponse

from domain.exceptions import (
    AppError,
    NotFoundError,
    ConflictError,
    ValidationError as DomainValidationError,
    RepositoryError,
)
from .http_errors import error_response, ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

def get_request_id(request: Request) -> str:
    """Get or generate a request ID from headers or generate a new one."""
    return (
        request.headers.get("X-Request-ID") or 
        request.headers.get("X-Correlation-ID") or 
        f"req-{str(uuid.uuid4())[:8]}"
    )

def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers for the FastAPI application.
    
    This includes:
    - Custom AppError hierarchy
    - Request validation errors
    - Pydantic validation errors
    - Unhandled exceptions
    """
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """Handle all custom application errors."""
        request_id = get_request_id(request)
        
        # Log the error with request context
        logger.error(
            "Application error: %s",
            exc.message,
            extra={
                "request_id": request_id,
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method,
            },
        )
        
        return error_response(
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        request_id = get_request_id(request)
        
        # Format validation errors in a more user-friendly way
        details = []
        for error in exc.errors():
            loc = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            details.append({
                "loc": loc,
                "msg": error["msg"],
                "type": error["type"],
            })
        
        logger.warning(
            "Request validation failed",
            extra={
                "request_id": request_id,
                "details": details,
                "path": request.url.path,
                "method": request.method,
            },
        )
        
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="validation_error",
            message="Request validation failed",
            details=details,
            request_id=request_id,
        )

    @app.exception_handler(404)
    async def handle_not_found(request: Request, exc: Exception) -> JSONResponse:
        """Handle 404 Not Found errors."""
        request_id = get_request_id(request)
        
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="not_found",
            message="The requested resource was not found",
            details={"path": request.url.path},
            request_id=request_id,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all other unhandled exceptions."""
        request_id = get_request_id(request)
        
        # Log the full exception with traceback
        logger.error(
            "Unhandled exception: %s",
            str(exc),
            exc_info=exc,
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
            },
        )
        
        # In production, don't expose internal error details
        if app.debug:
            details = {
                "type": exc.__class__.__name__,
                "message": str(exc),
            }
        else:
            details = None
        
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="internal_server_error",
            message="An unexpected error occurred",
            details=details,
            request_id=request_id,
        )
