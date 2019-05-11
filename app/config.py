from os import environ

client_id = environ["PODBEAN_CLIENT_ID"]
client_secret = environ["PODBEAN_CLIENT_SECRET"]

youtube_api_key = environ["YOUTUBE_API_KEY"]
channel_id = environ["YOUTUBE_CHANNEL_ID"]

title_pattern = environ.get("YOUTUTBE_TITLE_PATTERN", default=".+")

access_code_pickle_path = environ.get(
    "ACCESS_CODE_PICKLE_PATH", default="access_code.pickle"
)
published_after_pickle_path = environ.get(
    "PUBLISHED_AFTER_PICKLE_PATH", default="published_after.pickle"
)
