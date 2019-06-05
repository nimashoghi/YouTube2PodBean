from typing import Tuple

import aiohttp

from app.logging import create_logger
from app.sync import asyncify

logger, log = create_logger(__name__)


async def fetch_text(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()


async def fetch_json(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


def color_tuple_to_int(color: Tuple[float, float, float]) -> int:
    red, green, blue = color

    return (
        ((int(red) & 0xFF) << (0x2 * 0x8))
        | ((int(green) & 0xFF) << (0x1 * 0x8))
        | ((int(blue) & 0xFF) << (0x0 * 0x8))
    )


@asyncify
@log
def load_pickle(path, get_default=None, *, logger=logger):
    from pickle import dump, load

    try:
        with open(path, "rb") as f:
            value = load(f)
    except (OSError, IOError):
        if get_default is None:
            raise
        value = get_default()
        with open(path, "wb") as f:
            dump(value, f)

    return value


@asyncify
@log
def save_pickle(path, object, *, logger=logger):
    from pickle import dump

    with open(path, "wb") as f:
        dump(object, f)


@log
def sanitize_title(title: str, *, logger=logger) -> str:
    sanitized = "".join(
        [c for c in title if c.isalpha() or c.isdigit() or c == " "]
    ).rstrip()

    if sanitized == title:
        logger.info(f"Sanitized title '{title}' to '{sanitized}'")
    else:
        logger.debug(f"No need to sanitize '{title}'")

    return sanitized
