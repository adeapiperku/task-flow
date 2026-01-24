# worker/runner.py
"""
Task Flow Worker - Main Entry Point

This is the main entry point for the worker process. It provides a simple
CLI interface to start a worker with the specified configuration.

Production-ready worker implementation with:
- Executor abstraction (python_async, thread_pool, http)
- Capability-based job routing
- Lease management with heartbeats
- Concurrency control and backpressure
- Structured JSON logging
- Contextual error handling
"""
import asyncio
import argparse
import json
import logging
import sys
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, Optional, Set

from pythonjsonlogger import jsonlogger
from worker import Worker


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Task Flow Worker")
    
    parser.add_argument(
        "--queue",
        type=str,
        default="default",
        help="Queue name to process (default: default)",
    )
    
    parser.add_argument(
        "--worker-id",
        type=str,
        default=None,
        help="Worker ID (auto-generated if not provided)",
    )
    
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Seconds to wait when no jobs are available (default: 1.0)",
    )
    
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Maximum number of concurrent jobs (default: 4)",
    )
    
    parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=30.0,
        help="Seconds between heartbeats (default: 30.0)",
    )
    
    parser.add_argument(
        "--capability",
        action="append",
        dest="capabilities",
        help="Add a worker capability (can be specified multiple times)",
    )
    
    parser.add_argument(
        "--no-prefer-db",
        action="store_false",
        dest="prefer_db",
        help="Don't prefer DB job definitions over plugin ones",
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )
    
    return parser.parse_args()


class ContextFilter(logging.Filter):
    """Add contextual information to log records."""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record):
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class JsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that includes additional context."""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname


def setup_logging(level: str = "INFO", context: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """
    Configure structured JSON logging with context.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        context: Additional context to include in all log messages
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    handler.setFormatter(formatter)
    
    # Add context filter
    context_filter = ContextFilter(context)
    handler.addFilter(context_filter)
    
    logger.addHandler(handler)
    
    # Configure third-party loggers
    logging.getLogger('asyncio').setLevel('WARNING')
    logging.getLogger('urllib3').setLevel('WARNING')
    
    return logger


async def main() -> None:
    """
    Main entry point for the worker.
    
    Handles worker initialization, execution, and graceful shutdown.
    """
    args = parse_args()
    
    # Generate worker ID if not provided
    worker_id = args.worker_id or f"worker-{str(uuid.uuid4())[:8]}"
    
    # Set up logging with context
    logger = setup_logging(
        level=args.log_level,
        context={
            'worker_id': worker_id,
            'queue': args.queue,
            'service': 'task-flow-worker',
        }
    )
    
    # Log startup information
    logger.info(
        "Starting worker",
        extra={
            'capabilities': args.capabilities,
            'concurrency': args.concurrency,
            'poll_interval': args.poll_interval,
            'heartbeat_interval': args.heartbeat_interval,
        }
    )
    
    # Convert capabilities to a set
    capabilities: Set[str] = set(args.capabilities) if args.capabilities else set()
    
    try:
        # Create and run worker
        worker = Worker(
            queue=args.queue,
            worker_id=worker_id,
            poll_interval=args.poll_interval,
            prefer_db=args.prefer_db,
            capabilities=capabilities,
            concurrency=args.concurrency,
            heartbeat_interval_s=args.heartbeat_interval,
        )
        
        logger.info("Worker initialized and starting")
        await worker.run()
        
    except asyncio.CancelledError:
        logger.info("Worker received cancellation signal, shutting down")
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as exc:
        logger.error(
            "Worker failed with unexpected error",
            exc_info=True,
            extra={
                'error_type': exc.__class__.__name__,
                'error_details': str(exc),
            }
        )
        # Exit with non-zero status code to indicate error
        sys.exit(1)
    finally:
        # Ensure all logs are flushed
        logging.shutdown()


def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions and log them before exiting."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Call the default excepthook for keyboard interrupts
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Log the uncaught exception
    logger = logging.getLogger(__name__)
    logger.critical(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    
    # Exit with error code
    sys.exit(1)


if __name__ == "__main__":
    # Set up global exception handler
    sys.excepthook = handle_exception
    
    # Run the main async function
    try:
        asyncio.run(main())
    except Exception as exc:
        # This should be caught by the global excepthook
        sys.exit(1)
