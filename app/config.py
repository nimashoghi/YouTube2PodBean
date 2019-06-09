import re
from functools import reduce
from json import dump, load
from os import environ
from typing import Any, Callable, Union

from app.logging import create_logger

logger, log = create_logger(__name__)


def parse_config_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    match = re.search(r"^\s*\$env:(\w+)\s*$", value)
    if not match:
        return value
    env_variable_name = match[1]
    return value.replace(match[0], environ[env_variable_name])


@log
def config(
    config_name: str, default: Any = None, *, logger=logger
) -> Callable[[], Any]:
    config_names = config_name.split(":")

    def retrieve() -> Any:
        logger.debug(f"Trying to get the config value for setting '{config_name}'")

        from os import path

        settings_file = environ.get("SETTINGS_FILE", "settings.json")

        if not path.exists(settings_file):
            with open(settings_file, "w") as f:
                dump({}, f)

        with open(settings_file, "r") as f:
            json = load(f)

        try:
            value = reduce(lambda acc, update: acc[update], config_names, json)
            if not value and default is not None:
                value = default
                logger.debug(f"Using default value for config = {value}")
            else:
                logger.debug(f"Got config value = {value}")
        except Exception:
            if default is not None:
                value = default
                logger.debug(f"Using default value for config = {value}")
            else:
                raise
        return parse_config_value(value)

    return retrieve


@log
def get_public_ip(*, logger=logger) -> str:
    from requests import get

    result = get("https://api.ipify.org")
    if result.ok:
        return result.text
    else:
        logger.warn("Failed to get public IP address. Using localhost instead.")
        return "localhost"


enabled = config("Enabled", default=False)

host = config("Server:Host", default="0.0.0.0")
port = config("Server:Port", default="23808")
public_host = config("Server:PublicHost", default=get_public_ip())

podbean_enabled = config("PodBean:Enabled", default=False)
client_id = config("PodBean:ClientId")
client_secret = config("PodBean:ClientSecret")

youtube_enabled = config("YouTube:Enabled", default=False)
youtube_api_key = config("YouTube:ApiKey")
start_from = config("YouTube:StartFrom", default="")
video_process_delay = config("YouTube:VideoProcessDelay", default=10.0)
channel_id = config("YouTube:ChannelId")
polling_rate = config("YouTube:PollingRate", default=60.0)
title_pattern = config("YouTube:TitlePattern", default=".+")
title_negative_pattern = config("YouTube:TitleNegativePattern", default="")
videos = config("YouTube:CustomVideos", default=[])

webhook_enabled = config("WebHook:Enabled", default=False)
webhook_url_list = config("WebHook:UrlList", default=[])
webhook_text_max_length = config("WebHook:TextMaxLength", default=100)
webhook_default_avatar = config("WebHook:DefaultAvatar", default="")

wp_enabled = config("WordPress:Enabled", default=False)
wp_xmlrpc_url = config("WordPress:XmlRpcUrl", default="")
wp_username = config("WordPress:Username", default="")
wp_password = config("WordPress:Password", default="")
wp_embed_width = config("WordPress:EmbedWidth", default=560)
wp_embed_height = config("WordPress:EmbedHeight", default=315)

access_code_pickle_path = config(
    "Pickle:AccessCode", default="pickles/access_code.pickle"
)
processed_pickle_path = config("Pickle:Processed", default="pickles/processed.pickle")
playlist_history_pickle_path = config(
    "Pickle:PlaylistHistory", default="pickles/playlist_history.pickle"
)
