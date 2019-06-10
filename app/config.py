import json
import os
import re
from functools import reduce

import requests


def parse_config_value(value: str) -> str:
    if not isinstance(value, str):
        return value

    match = re.search(r"^\s*\$env:(\w+)\s*$", value)
    if not match:
        return value

    env_variable_name = match[1]
    return value.replace(match[0], os.environ[env_variable_name])


def config(config_name: str, default=None):
    config_names = config_name.split(":")

    def retrieve():

        settings_file = os.environ.get("SETTINGS_FILE", "settings.json")

        if not os.path.exists(settings_file):
            with open(settings_file, "w") as f:
                json.dump({}, f)

        with open(settings_file, "r") as f:
            data = json.load(f)

        try:
            value = reduce(lambda acc, update: acc[update], config_names, data)
            if not value and default is not None:
                value = default
        except:
            if default is not None:
                value = default
            else:
                raise
        return parse_config_value(value)

    return retrieve


def get_public_ip() -> str:
    return requests.get("https://api.ipify.org").text


enabled = config("Enabled", default=True)

host = config("Server:Host", default="0.0.0.0")
port = config("Server:Port", default="23808")
public_host = config("Server:PublicHost", default=get_public_ip())

podbean_enabled = config("PodBean:Enabled", default=True)
client_id = config("PodBean:ClientId")
client_secret = config("PodBean:ClientSecret")

youtube_enabled = config("YouTube:Enabled", default=True)
youtube_api_key = config("YouTube:ApiKey")
start_from = config("YouTube:StartFrom", default="")
video_process_delay = config("YouTube:VideoProcessDelay", default=10.0)
channel_id = config("YouTube:ChannelId")
polling_rate = config("YouTube:PollingRate", default=60.0)
title_pattern = config("YouTube:TitlePattern", default=".+")
title_negative_pattern = config("YouTube:TitleNegativePattern", default="")
videos = config("YouTube:CustomVideos", default=[])

webhook_enabled = config("WebHook:Enabled", default=True)
webhook_url_list = config("WebHook:UrlList", default=[])
webhook_text_max_length = config("WebHook:TextMaxLength", default=100)
webhook_default_avatar = config(
    "WebHook:DefaultAvatarUrl", default="https://i.imgur.com/eYw9nVR.jpg"
)

wp_enabled = config("WordPress:Enabled", default=True)
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
