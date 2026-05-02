"""
utils/logging.py
Structured logging via structlog.
Every log entry includes agent_id, session_id, pipeline automatically.
"""
import logging
import structlog
from config.settings import settings


def setup_logging() -> None:
    """Call once at app startup."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Suppress noisy third-party loggers
    logging.getLogger("langchain_core.tracers").setLevel(logging.CRITICAL)
    logging.getLogger("langsmith").setLevel(logging.ERROR)
    logging.getLogger("botocore").setLevel(logging.CRITICAL)
    logging.getLogger("boto3").setLevel(logging.CRITICAL)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.is_development
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    return structlog.get_logger(name)
