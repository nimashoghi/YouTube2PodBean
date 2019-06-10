import logging
from datetime import datetime

import dateutil
import pafy
import requests
from colorthief import ColorThief
from discord_webhook import DiscordEmbed, DiscordWebhook


def color_tuple_to_int(tuple):
    r, g, b = tuple
    return (
        ((r & 0xFF) << (0x2 * 0x8))
        | ((b & 0xFF) << (0x1 * 0x8))
        | ((g & 0xFF) << (0x0 * 0x8))
    )


def get_avatar(username):
    try:
        logging.debug(f"Trying to get avatar for YouTube username {username}")
        result = requests.get(
            f"https://www.googleapis.com/youtube/v3/channels?part=snippet&fields=items%2Fsnippet%2Fthumbnails%2Fdefault&forUsername={username}&key={pafy.g.api_key}"
        ).json()

        return result["items"][0]["snippet"]["thumbnails"]["default"]["url"]
    except:
        from app.config import webhook_default_avatar

        default = webhook_default_avatar()
        logging.debug(
            f"Could not get avatar. Using default avatar ({default}) instead."
        )
        return default


def clip_text(text):
    from app.config import webhook_text_max_length

    length = webhook_text_max_length()
    return f"{text[:length]}..." if len(text) > length else text


def send_webhook(video, jpg, avatar_url, webhook_url):
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
    embed.set_timestamp(dateutil.parser.parse(video.published).isoformat())
    embed.set_thumbnail(url=video.bigthumbhd, width=480, height=360)
    # embed.set_image(url=video.bigthumbhd, width=480, height=360)
    embed.set_footer(text=f"Duration: {video.duration}")

    webhook.add_embed(embed)
    webhook.execute()


def process_webhooks(video, jpg):
    from app.config import webhook_enabled

    if not webhook_enabled():
        logging.info(
            f'Discord WebHook posting not enabled. Skipping sending "{video.title}" to Discord.'
        )
        return

    from app.config import webhook_url_list

    avatar_url = get_avatar(video.username)

    for webhook_url in webhook_url_list():
        logging.debug(
            f"Sending Discord WebHook for '{video.title}' to the following Discord WebHook url: {webhook_url}"
        )
        send_webhook(video, jpg, avatar_url, webhook_url)

    logging.info(f'Successfully sent Discord WebHook for "{video.title}"')
