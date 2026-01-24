"""
HTTP error handling utilities for FastAPI.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional, Type, TypeVar, Generic, Union

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from domain.exceptions import (
    AppError,
    NotFoundError,
    ConflictError,
    ValidationError as DomainValidationError,
    RepositoryError,
)

logger = logging.getLogger(__name__)

class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: ErrorDetail

class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str
    message: str
    details: Optional[Union[Dict[str, Any], list]] = None
    request_id: Optional[str] = None


def error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Any = None,
    request_id: str = None,
) -> JSONResponse:
    """Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        error_code: Application-specific error code
        message: Human-readable error message
        details: Additional error details
        request_id: Request ID for tracing
        
    Returns:
        JSONResponse: Formatted error response
    """
    error = ErrorDetail(
        code=error_code,
        message=message,
        details=details,
        request_id=request_id,
    )
    
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(ErrorResponse(error=error)),
    )
