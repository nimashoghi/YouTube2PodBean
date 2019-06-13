import asyncio
import pickle
from logging import getLogger
from typing import Any

import aiofiles

logging = getLogger(__name__)


async def load_pickle(path: str, get_default=None) -> Any:
    logging.debug(
        f"Loading pickle file at '{path}'. Default value {'exists' if get_default is not None else 'does not exist'}."
    )
    try:
        async with aiofiles.open(path, mode="rb") as f:
            value = pickle.loads(await f.read())
    except (OSError, IOError):
        if get_default is None:
            logging.error(
                f"Could not load pickle file at '{path}' and no default value was provided."
            )
            raise
        else:
            logging.debug(
                f"Could not load pickle file '{path}'. Loading and writing default value to file."
            )
        if asyncio.iscoroutinefunction(get_default):
            value = await get_default()
        else:
            value = get_default()
        async with aiofiles.open(path, mode="wb") as f:
            await f.write(pickle.dumps(value))
    else:
        logging.debug(
            f"Successfully loaded pickle file at '{path}'. Object is of type '{type(value)}'."
        )

    return value


async def save_pickle(path: str, object: Any) -> Any:
    logging.debug(
        f"Saving object of type {type(object)} to the pickle file located at {path}."
    )

    async with aiofiles.open(path, mode="wb") as f:
        await f.write(pickle.dumps(object))

    return object
