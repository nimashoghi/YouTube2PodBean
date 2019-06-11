import os
import os.path
import pickle
import random
import re
import string
import tempfile
from logging import getLogger
from typing import Callable

import requests

URL_REGEX = r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'\".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"""

logging = getLogger(__name__)


def get_public_ip() -> str:
    return requests.get("https://api.ipify.org").text


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

    return object


def color_tuple_to_int(tuple):
    r, g, b = tuple
    return (
        ((r & 0xFF) << (0x2 * 0x8))
        | ((b & 0xFF) << (0x1 * 0x8))
        | ((g & 0xFF) << (0x0 * 0x8))
    )


def clip_text(text: str, length: int) -> str:
    return f"{text[:length]}..." if len(text) > length else text


def get_url_extension(url, default="jpg"):
    match = re.search(url, r"\.(.+)\s*$")
    return match[1] if match else default


def make_temp_file(
    prefix: str,
    suffix: str,
    directory: str = f"{tempfile.gettempdir()}/youtube2podbean",
) -> str:
    if not os.path.isdir(directory):
        os.mkdir(directory)
    random_string = "".join(random.choice(string.ascii_lowercase) for _ in range(6))
    return f"{directory}/{prefix}{random_string}{suffix}"
