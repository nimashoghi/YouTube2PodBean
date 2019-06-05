import pickle
from json import dump, load

from app.logging import create_logger

logger, log = create_logger(__name__)


@log
def load_pickle(path, get_default=None, *, logger=logger):
    try:
        with open(path, "rb") as f:
            value = pickle.load(f)
    except (OSError, IOError):
        if get_default is None:
            raise
        value = get_default()
        with open(path, "wb") as f:
            pickle.dump(value, f)

    return value


@log
def save_pickle(path, object, *, logger=logger):
    with open(path, "wb") as f:
        pickle.dump(object, f)


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
