"""
Enhanced logging configuration for OCR Backend API with production-grade features.
"""

import os
import gc
import gzip
import shutil
import logging
import logging.handlers
import contextvars
import threading
from pathlib import Path
from typing import Optional
import queue
import time
import re

import coloredlogs

from config.settings import get_settings

# Context variable for request ID tracking
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='N/A')


class SensitiveDataFilter(logging.Filter):
    """Filter to sanitize sensitive data from log messages."""
    
    def __init__(self, enabled: bool = True):
        super().__init__()
        self.enabled = enabled
        
        # Patterns for sensitive data
        self.patterns = [
            # Base64 encoded data (typically images)
            (re.compile(r'data:image/[^;]+;base64,[A-Za-z0-9+/]{100,}'), '[BASE64_IMAGE_DATA]'),
            (re.compile(r'[A-Za-z0-9+/]{500,}={0,2}'), '[LARGE_BASE64_DATA]'),
            # API keys and tokens
            (re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]{20,})', re.IGNORECASE), 'api_key="[REDACTED]"'),
            (re.compile(r'token["\']?\s*[:=]\s*["\']?([A-Za-z0-9_.-]{20,})', re.IGNORECASE), 'token="[REDACTED]"'),
            # Email addresses (partial masking)
            (re.compile(r'\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'), r'\1***@\2'),
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        if not self.enabled:
            return True
            
        # Sanitize the message
        if hasattr(record, 'msg') and record.msg:
            message = str(record.msg)
            for pattern, replacement in self.patterns:
                message = pattern.sub(replacement, message)
            record.msg = message
            
        # Sanitize arguments
        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in self.patterns:
                        arg = pattern.sub(replacement, arg)
                sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        return True


class CompressedRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Enhanced rotating file handler with compression support."""
    
    def __init__(self, *args, compress: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.compress = compress
    
    def doRollover(self):
        """Enhanced rollover with optional compression."""
        super().doRollover()
        
        if self.compress and self.backupCount > 0:
            # Compress the most recent backup file
            backup_file = f"{self.baseFilename}.1"
            if os.path.exists(backup_file):
                compressed_file = f"{backup_file}.gz"
                try:
                    with open(backup_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    os.remove(backup_file)
                except Exception as e:
                    # If compression fails, keep the original file
                    pass


class AsyncLogHandler(logging.Handler):
    """Asynchronous log handler to prevent I/O blocking."""
    
    def __init__(self, handler: logging.Handler, queue_size: int = 10000):
        super().__init__()
        self.handler = handler
        self.queue = queue.Queue(maxsize=queue_size)
        self.thread = None
        self.shutdown_flag = threading.Event()
        self._start_thread()
    
    def _start_thread(self):
        """Start the background logging thread."""
        self.thread = threading.Thread(target=self._log_worker, daemon=True)
        self.thread.start()
    
    def _log_worker(self):
        """Background thread worker to process log records."""
        while not self.shutdown_flag.is_set():
            try:
                record = self.queue.get(timeout=1)
                if record is None:  # Sentinel to stop
                    break
                self.handler.emit(record)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                # Don't let logging errors crash the application
                pass
    
    def emit(self, record: logging.LogRecord):
        """Add record to queue for async processing."""
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            # If queue is full, drop the record to prevent blocking
            pass
    
    def close(self):
        """Clean shutdown of async handler."""
        self.shutdown_flag.set()
        self.queue.put(None)  # Sentinel
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        self.handler.close()
        super().close()


class RequestContextFormatter(logging.Formatter):
    """Custom formatter that includes request context information."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Add request ID to the record
        record.request_id = request_id_var.get()
        
        # Add memory usage info for debugging
        if hasattr(record, 'levelno') and record.levelno >= logging.WARNING:
            record.memory_mb = f"{gc.get_stats()[0]['collections']}"
        
        return super().format(record)


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Set up and configure an enhanced logger with production-grade features.
    
    Args:
        name: The name of the logger (typically __name__ from the calling module)
        
    Returns:
        logging.Logger: Enhanced configured logger instance
    """
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if logger already exists
    if logger.handlers:
        return logger
        
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Create logs directory if it doesn't exist
    log_file_path = Path(settings.LOG_FILE)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create enhanced formatter with request context
    formatter = RequestContextFormatter(
        fmt=settings.LOG_FORMAT,
        datefmt=settings.LOG_DATE_FORMAT
    )
    
    # Create enhanced file handler with compression support
    file_handler = CompressedRotatingFileHandler(
        filename=settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_SIZE,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8',
        compress=settings.LOG_ENABLE_COMPRESSION
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Add sensitive data filter if enabled
    if settings.LOG_SANITIZE_SENSITIVE:
        sensitive_filter = SensitiveDataFilter(enabled=True)
        file_handler.addFilter(sensitive_filter)
    
    # Wrap file handler with async handler if enabled
    if settings.LOG_ASYNC_ENABLED:
        async_file_handler = AsyncLogHandler(
            handler=file_handler,
            queue_size=settings.LOG_QUEUE_SIZE
        )
        final_file_handler = async_file_handler
    else:
        final_file_handler = file_handler
    
    # Create console handler with colored output (simpler format for readability)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Configure coloredlogs for console output with enhanced format
    coloredlogs.install(
        level=settings.LOG_LEVEL.upper(),
        logger=logger,
        fmt="%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
        field_styles={
            'asctime': {'color': 'green'},
            'hostname': {'color': 'magenta'},
            'levelname': {'bold': True, 'color': 'black'},
            'name': {'color': 'blue'},
            'funcName': {'color': 'cyan'},
            'lineno': {'color': 'yellow'},
            'programname': {'color': 'cyan'},
            'username': {'color': 'yellow'}
        },
        level_styles={
            'critical': {'bold': True, 'color': 'red'},
            'debug': {'color': 'green'},
            'error': {'color': 'red'},
            'info': {'color': 'white'},
            'notice': {'color': 'magenta'},
            'spam': {'color': 'green', 'faint': True},
            'success': {'bold': True, 'color': 'green'},
            'verbose': {'color': 'blue'},
            'warning': {'color': 'yellow'}
        }
    )
    
    # Add handlers to logger
    logger.addHandler(final_file_handler)
    
    # Disable propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger


def get_logger(name: str = __name__) -> logging.Logger:
    """
    Get or create a logger instance.
    
    Args:
        name: The name of the logger
        
    Returns:
        logging.Logger: Logger instance
    """
    return setup_logger(name)


def set_request_id(request_id: str) -> None:
    """
    Set the request ID for the current context.
    
    Args:
        request_id: Unique identifier for the request
    """
    request_id_var.set(request_id)


def get_request_id() -> str:
    """
    Get the current request ID.
    
    Returns:
        str: Current request ID or 'N/A' if not set
    """
    return request_id_var.get()


def log_performance(logger: logging.Logger, operation: str, start_time: float, **kwargs) -> None:
    """
    Log performance metrics for an operation.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        start_time: Start time (from time.time())
        **kwargs: Additional context to log
    """
    duration = time.time() - start_time
    context = " ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"PERF: {operation} completed in {duration:.3f}s {context}".strip())


def log_memory_usage(logger: logging.Logger, context: str = "") -> None:
    """
    Log current memory usage statistics.
    
    Args:
        logger: Logger instance
        context: Additional context for the log
    """
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.debug(f"MEMORY: {memory_mb:.1f}MB RSS {context}".strip())
    except ImportError:
        # psutil not available, use garbage collector stats
        gc_stats = gc.get_stats()
        logger.debug(f"MEMORY: GC collections={gc_stats[0]['collections']} {context}".strip()) 