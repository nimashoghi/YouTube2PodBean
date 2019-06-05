from typing import Tuple

from pafy.backend_youtube_dl import YtdlPafy

from app.logging import create_logger

logger, log = create_logger(__name__)


def color_tuple_to_int(color: Tuple[float, float, float]) -> int:
    red, green, blue = color

    return (
        ((red & 0xFF) << (0x2 * 0x8))
        | ((green & 0xFF) << (0x1 * 0x8))
        | ((blue & 0xFF) << (0x0 * 0x8))
    )


@log
def get_avatar(username: str, *, logger=logger) -> str:
    from requests import get
    from pafy import g

    result = get(
        f"https://www.googleapis.com/youtube/v3/channels?part=snippet&fields=items%2Fsnippet%2Fthumbnails%2Fdefault&forUsername={username}&key={g.api_key}"
    ).json()

    try:
        return result["items"][0]["snippet"]["thumbnails"]["default"]["url"]
    except KeyError:
        logger.warn(
            f"Could not get the avatar for channel with username = '{username}'. Using default avatar"
        )
        from app.config import webhook_default_avatar

        return webhook_default_avatar()


@log
def clip_text(text: str, *, logger=logger) -> str:
    from app.config import webhook_text_max_length

    length = webhook_text_max_length()
    clipped_text = f"{text[:length]}..." if len(text) > length else text
    logger.debug(f"Clipping text to '{clipped_text}'")
    return clipped_text


@log
def send_webhook(
    video: YtdlPafy, jpg: str, avatar_url: str, webhook_url: str, *, logger=logger
) -> None:
    from dateutil import parser
    from discord_webhook import DiscordEmbed, DiscordWebhook
    from datetime import datetime
    from colorthief import ColorThief

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


def post_to_discord(video: YtdlPafy, jpg: str) -> None:
    from app.config import webhook_enabled

    if not webhook_enabled():
        print(
            f'Discord WebHook posting not enabled. Skipping sending "{video.title}" to Discord.'
        )
        return

    from app.config import webhook_url_list
    from dateutil import parser
    from discord_webhook import DiscordEmbed, DiscordWebhook

    avatar_url = get_avatar(video.username)

    for webhook_url in webhook_url_list():
        send_webhook(video, jpg, avatar_url, webhook_url)

    print(f'Successfully sent Discord webhooks for "{video.title}"')
