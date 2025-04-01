import os
import loguru
import sys


def configure_logging():
    log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    
    loguru.logger.remove()
    if os.getenv("LOG_LEVEL") is None:
        loguru.logger.add(sys.stdout, format=log_format, level="INFO")
        loguru.logger.info("No LOG_LEVEL environment variable set, using INFO level")
    else:
        loguru.logger.add(sys.stdout, format=log_format, level=os.getenv("LOG_LEVEL"))
        loguru.logger.info(f"Logging level set to {os.getenv('LOG_LEVEL')}")
    
    return loguru.logger

logger = configure_logging()