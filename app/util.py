import pickle
from logging import getLogger

logging = getLogger(__name__)


def sanitize_title(title):
    return "".join(
        [c for c in title if c.isalpha() or c.isdigit() or c == " "]
    ).rstrip()


def load_pickle(path, get_default=None):
    logging.debug(
        f"Loading pickle file at '{path}'. Default value {'exists' if get_default is not None else 'does not exist'}."
    )
    try:
        with open(path, "rb") as f:
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
        value = get_default()
        with open(path, "wb") as f:
            pickle.dump(value, f)
    else:
        logging.debug(
            f"Successfully loaded pickle file at '{path}'. Object is of type '{type(value)}'."
        )

    return value


def save_pickle(path, object):
    logging.debug(
        f"Saving object of type {type(object)} to the pickle file located at {path}."
    )

    with open(path, "wb") as f:
        pickle.dump(object, f)
