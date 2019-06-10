import pickle


def sanitize_title(title):
    return "".join(
        [c for c in title if c.isalpha() or c.isdigit() or c == " "]
    ).rstrip()


def load_pickle(path, get_default=None):
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


def save_pickle(path, object):
    with open(path, "wb") as f:
        pickle.dump(object, f)
