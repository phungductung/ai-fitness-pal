import logging
import sys
import json
import os
from datetime import datetime
from contextvars import ContextVar
from typing import Any, Dict

# Context variable to store thread_id for the current request
thread_id_var: ContextVar[str] = ContextVar("thread_id", default="no_thread")

class CustomLogger(logging.Logger):
    """Custom logger to support extra_fields keyword argument."""
    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=1, **kwargs):
        extra_fields = kwargs.pop("extra_fields", None)
        if extra_fields:
            if extra is None:
                extra = {}
            # The formatter expects extra_fields to be a direct attribute of the record
            extra["extra_fields"] = extra_fields
        
        super()._log(level, msg, args, exc_info=exc_info, extra=extra, stack_info=stack_info, stacklevel=stacklevel)

# Set the custom logger class before any loggers are created
logging.setLoggerClass(CustomLogger)

class StructuredFormatter(logging.Formatter):
    """Custom formatter to output JSON logs."""
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "thread_id": thread_id_var.get(),
        }
        
        # Add extra fields if they exist
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
            
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def setup_logger(name: str = "fitness_app", level: int = logging.INFO) -> logging.Logger:
    """Initialize and configure the logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter())
        logger.addHandler(console_handler)
        
        # File handler (optional, but good for persistence)
        log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, "backend.log"))
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)
        
    return logger

# Pre-initialize the main logger
logger = setup_logger()

def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance, optionally with a specific name."""
    if name:
        return setup_logger(name)
    return logger
