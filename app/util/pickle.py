import asyncio
import pickle
from logging import getLogger
from typing import Any

logging = getLogger(__name__)


async def load_pickle(path: str, get_default=None) -> Any:
    logging.debug(
        f"Loading pickle file at '{path}'. Default value {'exists' if get_default is not None else 'does not exist'}."
    )
    try:
        with open(path, mode="rb") as f:
            value = pickle.load(f)
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
        with open(path, mode="wb") as f:
            pickle.dump(value, f)
    else:
        logging.debug(
            f"Successfully loaded pickle file at '{path}'. Object is of type '{type(value)}'."
        )

    return value


async def save_pickle(path: str, object: Any) -> Any:
    logging.debug(
        f"Saving object of type {type(object)} to the pickle file located at {path}."
    )

    with open(path, mode="wb") as f:
        pickle.dump(object, f)

    return object


async def is_already_posted(id: str, get_pickle_path) -> bool:
    pickle_path: str = await get_pickle_path()
    posted_set = await load_pickle(pickle_path, get_default=lambda: set([]))
    return id in posted_set


async def mark_as_posted(id: str, get_pickle_path):
    pickle_path: str = await get_pickle_path()
    post_history = await load_pickle(pickle_path, get_default=lambda: set([]))
    await save_pickle(pickle_path, set([id, *post_history]))
