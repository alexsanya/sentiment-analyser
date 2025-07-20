"""
Logging configuration for news-powered trading system.
Provides structured logging with file separation by log level.
"""

import logging
import logging.handlers
import os
from typing import Any, Dict

import structlog


def setup_logging(environment: str = "development") -> structlog.stdlib.BoundLogger:
    """
    Configure structured logging with file separation by log level.
    
    Args:
        environment: "development" or "production"
        
    Returns:
        Configured structlog logger
    """
    # Ensure logs directory exists
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=None,  # We'll handle streams via handlers
        level=logging.DEBUG
    )

    LOG_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Error log handler
    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(logs_dir, "error.log"),
        maxBytes=LOG_FILE_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    error_handler.setLevel(logging.ERROR)
    
    # Warning log handler
    warning_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(logs_dir, "warning.log"),
        maxBytes=LOG_FILE_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    warning_handler.setLevel(logging.WARNING)
    
    # Info log handler (all levels)
    info_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(logs_dir, "app.log"),
        maxBytes=LOG_FILE_SIZE,
        backupCount=LOG_BACKUP_COUNT
    )
    info_handler.setLevel(logging.INFO)

    handlers = [
        error_handler,
        warning_handler,
        info_handler
    ]
    
    # Console handler for development
    if environment == "development":
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        handlers.append(console_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if environment == "production":
        # JSON formatter for production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty formatter for development
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)