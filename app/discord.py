import asyncio
from typing import Tuple

import aiohttp
from pafy.backend_youtube_dl import YtdlPafy

from app.logging import create_logger
from app.sync import asyncify

logger, log = create_logger(__name__)


@log
async def get_avatar(username: str, *, logger=logger) -> str:
    from pafy import g
    from app.util import fetch_json

    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&fields=items%2Fsnippet%2Fthumbnails%2Fdefault&forUsername={username}&key={g.api_key}"

    result = await fetch_json(url)
    try:
        return result["items"][0]["snippet"]["thumbnails"]["default"]["url"]
    except KeyError:
        logger.warn(
            f"Could not get the avatar for channel '{username}'. Using default avatar."
        )
        from app.config import webhook_default_avatar

        return webhook_default_avatar()


@log
def clip_text(text: str, *, logger=logger) -> str:
    from app.config import webhook_text_max_length

    length = webhook_text_max_length()
    clipped_text = f"{text[:length]}..." if len(text) > length else text
    if clipped_text != text:
        logger.debug(f"Clipping text to '{clipped_text}'")
    return clipped_text


@asyncify
@log
def send_webhook(
    video: YtdlPafy, jpg: str, avatar_url: str, webhook_url: str, *, logger=logger
) -> None:
    from dateutil import parser
    from discord_webhook import DiscordEmbed, DiscordWebhook
    from colorthief import ColorThief
    from app.util import color_tuple_to_int

    logger.info(f"Sending Discord webhook message for '{video.title}'")

    webhook = DiscordWebhook(url=webhook_url)

    embed = DiscordEmbed()
    embed.set_url(video.watchv_url)
    embed.set_color(color_tuple_to_int(ColorThief(jpg).get_color(quality=1)))
    embed.set_title(video.title)
    embed.add_embed_field(name="Description", value=clip_text(video.description))
    embed.set_author(
        name=video.author,
        url=f"https://www.youtube.com/user/{video.username}",
        icon_url=avatar_url,
    )
    embed.set_timestamp(parser.parse(video.published).isoformat())
    embed.set_thumbnail(url=video.bigthumbhd, width=480, height=360)
    embed.set_footer(text=f"Duration: {video.duration}")

    webhook.add_embed(embed)
    webhook.execute()


@log
async def post_to_discord(video: YtdlPafy, jpg: str, *, logger=logger) -> None:
    from app.config import webhook_enabled, webhook_url_list

    if not webhook_enabled():
        logger.info(
            f'Discord WebHook posting not enabled. Skipping sending "{video.title}" to Discord.'
        )
        return

    avatar_url = await get_avatar(video.username)

    await asyncio.wait(
        {
            asyncio.create_task(send_webhook(video, jpg, avatar_url, webhook_url))
            for webhook_url in webhook_url_list()
        }
    )

    logger.info(f'Successfully sent Discord webhooks for "{video.title}"')
