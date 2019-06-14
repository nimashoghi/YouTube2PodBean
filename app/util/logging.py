import logging
import sys
import time
from typing import Callable


def setup_logging(module: str) -> logging.Logger:
    logger = logging.getLogger(module)

    log_filename = f"./logs/{module}-{time.strftime('%Y%m%d-%H%M%S')}.log"
    # log to both stderr and a file
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[logging.FileHandler(log_filename), logging.StreamHandler()],
    )
    logging.info(f"Logging to '{log_filename}'")

    def exception_handler(type, value, tb):
        logger.exception(f"Got an exception of type '{type}'", exc_info=value)

    # Install exception handler
    sys.excepthook = exception_handler

    return logger
