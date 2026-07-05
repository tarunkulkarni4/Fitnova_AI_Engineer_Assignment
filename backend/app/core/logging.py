import sys
import logging
from loguru import logger
from app.core.config import settings

class InterceptHandler(logging.Handler):
    """
    Intercepts standard library logs and forwards them to Loguru.
    """
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller frame
        frame = sys._getframe(6)
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back

        logger.opt(depth=0, exception=record.exc_info).log(
            level, record.getMessage()
        )

def setup_logging() -> None:
    # Intercept all logs at root level
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(settings.LOG_LEVEL)

    # Disable handlers of other library loggers and let them propagate to root
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    # Configure Loguru format
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "level": settings.LOG_LEVEL,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            }
        ]
    )
