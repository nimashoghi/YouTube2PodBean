import asyncio
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable


def setup_logging(module: str) -> logging.Logger:
    logger = logging.getLogger(module)

    log_filename = f"./logs/{module}-{time.strftime('%Y%m%d-%H%M%S')}.log"
    # log to both stderr and a file
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "DEBUG"),
        handlers=[logging.FileHandler(log_filename), logging.StreamHandler()],
    )
    logging.info(f"Logging to '{log_filename}'")

    def exception_handler(type, value, tb):
        logger.exception(f"Got an exception of type '{type}'", exc_info=value)

    # Install exception handler
    sys.excepthook = exception_handler

    return logger


def entrypoint(f, logger: logging.Logger):
    def exception_handler(loop, context):
        logger.exception(
            f"Received an exception of type '{type(context['exception'])}' with message '{context['message']}'.",
            exc_info=context["exception"],
        )
        return loop.default_exception_handler(context)

    async def wrapper():
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor())
        loop.set_exception_handler(exception_handler)
        return await f()

    return asyncio.run(wrapper())
