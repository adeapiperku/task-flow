# Worker Core Module
"""
This module contains the core functionality for the worker, including:
- Worker class for job processing
- Job dispatching and execution
- Registry management
- Utility functions and helpers
"""

# Re-export key components for easier imports
from .worker import Worker
from .dispatcher import dispatch_job, check_capabilities
from .registry import RegistryManager
from .models import WorkerConfig, WorkerStats
from .utils import run_with_timeout, setup_signal_handlers, create_task_with_callback
from .exceptions import WorkerError, WorkerShutdownError, WorkerConfigurationError

__all__ = [
    'Worker',
    'dispatch_job',
    'check_capabilities',
    'RegistryManager',
    'WorkerConfig',
    'WorkerStats',
    'run_with_timeout',
    'setup_signal_handlers',
    'create_task_with_callback',
    'WorkerError',
    'WorkerShutdownError',
    'WorkerConfigurationError',
]
