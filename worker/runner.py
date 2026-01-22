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
"""
import asyncio
import argparse
import logging
from typing import Set

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


def setup_logging(level: str = "INFO") -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


async def main() -> None:
    """Main entry point for the worker."""
    args = parse_args()
    setup_logging(args.log_level)
    
    # Convert capabilities to a set
    capabilities: Set[str] = set(args.capabilities) if args.capabilities else set()
    
    # Create and run worker
    worker = Worker(
        queue=args.queue,
        worker_id=args.worker_id,
        poll_interval=args.poll_interval,
        prefer_db=args.prefer_db,
        capabilities=capabilities,
        concurrency=args.concurrency,
        heartbeat_interval_s=args.heartbeat_interval,
    )
    
    try:
        await worker.run()
    except KeyboardInterrupt:
        logging.info("Worker stopped by user")
    except Exception as exc:
        logging.exception("Worker failed: %s", exc)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
