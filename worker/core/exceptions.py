"""Custom exceptions for the worker."""

class WorkerError(Exception):
    """Base exception for all worker-related errors."""
    pass

class WorkerShutdownError(WorkerError):
    """Raised when worker is shutting down."""
    pass

class WorkerConfigurationError(WorkerError):
    """Raised when there's an error in worker configuration."""
    pass
