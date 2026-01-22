"""Task Flow Worker - A production-ready background job processor."""

# Make core modules available at the package level
from worker.core.worker import Worker
from worker.core.dispatcher import dispatch_job, check_capabilities
from worker.core.registry import RegistryManager
from worker.core.models import WorkerConfig, WorkerStats
from worker.core.utils import run_with_timeout, setup_signal_handlers, create_task_with_callback
from worker.core.exceptions import WorkerError, WorkerShutdownError, WorkerConfigurationError

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
