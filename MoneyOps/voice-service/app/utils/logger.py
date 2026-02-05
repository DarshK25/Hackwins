"""
STRUCTURE LOGGING FOR VOICE SERVICE 
"""
import logging
import sys
import structlog

def setup_logging(log_level: str = "INFO") -> None:
    """
    Set up structured logging for the voice service.
    """
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class = structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__):
    """
    Get a structured logger instance.
    """
    return structlog.get_logger(name)