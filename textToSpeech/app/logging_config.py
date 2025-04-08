import os
import loguru
import sys


def configure_logging():

    loguru.logger.remove()
    if os.getenv("LOG_LEVEL") in (None, ""):
        loguru.logger.add(sys.stdout, level="INFO")
        loguru.logger.info("No LOG_LEVEL environment variable set, using INFO level")
    else:
        loguru.logger.add(sys.stdout, level=os.getenv("LOG_LEVEL"))
        loguru.logger.info(f"Logging level set to {os.getenv('LOG_LEVEL')}")
    
    return loguru.logger

logger = configure_logging()