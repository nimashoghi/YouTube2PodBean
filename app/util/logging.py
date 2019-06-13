import logging
import sys
import time
from typing import Callable


def setup_logging(module: str):
    log_filename = f"./logs/{module}-{time.strftime('%Y%m%d-%H%M%S')}.log"
    # log to both stderr and a file
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[logging.FileHandler(log_filename), logging.StreamHandler()],
    )
    logging.info(f"Logging to '{log_filename}'")


async def log_exceptions(f: Callable, logger: logging.Logger):
    try:
        await f()
    except BaseException as e:
        logger.exception(f"Received an exception of type '{type(e)}'", exc_info=e)
