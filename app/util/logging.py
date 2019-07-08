import asyncio
import logging
import logging.handlers
import multiprocessing as mp
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from discord_webhook import DiscordWebhook

from app.util import run_sync, split_by_length

DISCORD_WEBHOOK_CONTENT_MAX_LENGTH = 1900


def send_webhook_message(content: str, url: str):
    DiscordWebhook(url=url, content=content).execute()


def webhook_log_process(content: str, url: str):

    chunks = split_by_length(content, DISCORD_WEBHOOK_CONTENT_MAX_LENGTH)
    num_chunks = len(chunks)
    for i, chunk in enumerate(chunks):
        pre = ""
        post = ""
        if num_chunks > 1:
            if i != 0:
                pre = "..."
            if (i + 1) != num_chunks:
                post = "..."

        send_webhook_message(f"({i + 1}/{num_chunks}) {pre}{chunk}{post}", url)


class DiscordWebhookLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        from app.config.logging import logging_webhook_urls

        if record.levelno < logging.ERROR:
            return

        content = self.format(record)
        for url in logging_webhook_urls.sync():
            process = mp.Process(target=webhook_log_process, args=(content, url))
            process.start()


def setup_logging(module: str) -> logging.Logger:
    # log to both stderr and a file
    logging.basicConfig(
        format="[%(asctime)s - %(name)s - %(pathname)s:%(lineno)i] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=os.environ.get("LOG_LEVEL", "DEBUG"),
        handlers=[
            logging.StreamHandler(),
            logging.handlers.TimedRotatingFileHandler(
                filename=f"./logs/{module}", when="midnight"
            ),
            DiscordWebhookLogHandler(),
        ],
    )

    logger = logging.getLogger(module)
    logger.critical("STARTING LOGGING")

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
