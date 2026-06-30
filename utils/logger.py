import logging
import sys
from pathlib import Path
from loguru import logger as loguru_logger

def setup_logger(name: str = "market_agent"):
    """Set up logger with console and file output"""
    logger = loguru_logger
    logger.remove()  # Remove default handler
    
    # Add console handler
    logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}", level="INFO")
    
    # Add file handler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(log_dir / "{time:YYYY-MM-DD}.log", rotation="00:00", retention="30 days", level="DEBUG")
    
    return logger.bind(name=name)