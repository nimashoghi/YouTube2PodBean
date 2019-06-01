import pickle
from functools import reduce
from json import load
from os import environ


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


def parse_config_value(value):
    if not isinstance(value, str):
        return value

    import re

    match = re.search(r"^\s*\$env:(\w+)\s*$", value)
    if not match:
        return value
    env_variable_name = match[1]
    return value.replace(match[0], environ[env_variable_name])


def config(config_name: str, default=None):
    config_names = config_name.split(":")

    def retrieve():
        with open(environ.get("SETTINGS_FILE", "settings.json"), "r") as f:
            json = load(f)
        try:
            value = reduce(lambda acc, update: acc[update], config_names, json)
            if not value and default is not None:
                value = default
        except:
            if default is not None:
                value = default
            else:
                raise
        return parse_config_value(value)

    return retrieve


def get_public_ip():
    from requests import get

    return get("https://api.ipify.org").text


host = config("Server:Host", default="0.0.0.0")
port = config("Server:Port", default="23808")
public_host = config("Server:PublicHost", default=get_public_ip())

client_id = config("PodBean:ClientId")
client_secret = config("PodBean:ClientSecret")

youtube_api_key = config("YouTube:ApiKey")
start_from = config("YouTube:StartFrom", default="")
channel_id = config("YouTube:ChannelId")
polling_rate = config("YouTube:PollingRate", default=60.0)
title_pattern = config("YouTube:TitlePattern", default=".+")
title_negative_pattern = config("YouTube:TitleNegativePattern", default="")
videos = config("YouTube:CustomVideos", default=[])

access_code_pickle_path = config(
    "Pickle:AccessCode", default="pickles/access_code.pickle"
)
processed_pickle_path = config("Pickle:Processed", default="pickles/processed.pickle")
playlist_history_pickle_path = config(
    "Pickle:PlaylistHistory", default="pickles/playlist_history.pickle"
)
