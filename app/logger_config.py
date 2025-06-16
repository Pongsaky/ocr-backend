"""
Logging configuration for OCR Backend API.
"""

import os
import logging
import logging.handlers
from pathlib import Path

import coloredlogs

from config.settings import get_settings


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Set up and configure a logger with both file and console handlers.
    
    Args:
        name: The name of the logger (typically __name__ from the calling module)
        
    Returns:
        logging.Logger: Configured logger instance
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
    
    # Create formatter
    formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # Create file handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=settings.LOG_FILE,
        maxBytes=settings.LOG_MAX_SIZE,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Create console handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Configure coloredlogs for console output
    coloredlogs.install(
        level=settings.LOG_LEVEL.upper(),
        logger=logger,
        fmt=settings.LOG_FORMAT,
        field_styles={
            'asctime': {'color': 'green'},
            'hostname': {'color': 'magenta'},
            'levelname': {'bold': True, 'color': 'black'},
            'name': {'color': 'blue'},
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
    logger.addHandler(file_handler)
    
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