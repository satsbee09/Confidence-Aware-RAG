import sys
from pathlib import Path
from loguru import logger
from app.core.config import settings

def setup_logging() -> None:
    """
    Configures standardized logging using loguru.
    Outputs formatted, colorized logs to stderr and structured logs to file.
    """
    # Remove default handlers
    logger.remove()

    # Console Handler (Human-readable with colors)
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    log_level = "DEBUG" if settings.DEBUG else "INFO"

    logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )

    # File Handler (Rotating log file for persistent audit logs)
    log_dir = Path("./logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="14 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        compression="zip",
    )

    logger.info(f"Logging initialized. Log level: {log_level}, Environment: {settings.APP_ENV}")
