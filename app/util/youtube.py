from logging import getLogger

import aiohttp
import pafy

logging = getLogger(__name__)


async def get_avatar(username_or_channel_id: str) -> str:
    try:
        # if a channel does not have a proper username, `username_or_channel_id` will include the channel id
        username = None
        channel_id = None
        channel_info: dict = {}

        # channel ids start w/ UC and have 24 chars
        if len(username_or_channel_id) == 24 and username_or_channel_id.startswith(
            "UC"
        ):
            channel_id = username_or_channel_id
            channel_info = dict(id=channel_id)
        else:
            username = username_or_channel_id
            channel_info = dict(forUsername=username)

        logging.debug(
            "Trying to get avatar for YouTube channel with "
            + (f"channel id '{channel_id}'" if channel_id else f"username '{username}'")
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url="https://www.googleapis.com/youtube/v3/channels",
                params=dict(
                    part="snippet",
                    fields="items/snippet/thumbnails/default",
                    key=pafy.g.api_key,
                    **channel_info,
                ),
            ) as response:
                logging.debug(
                    f"Got the following response while trying to get avatar for user '{username_or_channel_id}': '{await response.text()}'"
                )
                json = await response.json()
                return json["items"][0]["snippet"]["thumbnails"]["default"]["url"]
    except BaseException as e:
        from app.config.youtube import youtube_default_avatar

        logging.exception(
            f"Got an exception of type {type(e)} when trying to get avatar for user '{username_or_channel_id}'.",
            exc_info=e,
        )

        default_avatar = await youtube_default_avatar()
        logging.critical(
            f"Could not get avatar. Using default avatar ({default_avatar}) instead."
        )
        return default_avatar
