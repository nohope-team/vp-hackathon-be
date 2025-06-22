import json
import sys
from datetime import datetime
from loguru import logger
from app.configs.settings import settings


def json_formatter(record):
    """Custom JSON formatter for structured logging"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["name"],
        "function": record["function"],
        "line": record["line"],
        "extra": record["extra"]
    }
    
    if record["exception"]:
        log_entry["exception"] = record["exception"]
    
    return json.dumps(log_entry, ensure_ascii=False)


def setup_logger():
    """Setup structured JSON logging"""
    logger.remove()  # Remove default handler
    
    # Console handler with JSON format
    logger.add(
        sys.stdout,
        format=json_formatter,
        level=settings.log_level,
        serialize=False
    )
    
    # File handler for local development
    if settings.environment == "development":
        logger.add(
            "logs/app.log",
            format=json_formatter,
            level=settings.log_level,
            rotation="1 day",
            retention="7 days",
            serialize=False
        )
    
    return logger


# Initialize logger
app_logger = setup_logger()