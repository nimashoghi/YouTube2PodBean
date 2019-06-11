from datetime import datetime
from logging import getLogger
from typing import Set

import dateutil.parser
import pafy.g
import requests
import rx
import rx.operators
from colorthief import ColorThief
from discord_webhook import DiscordEmbed, DiscordWebhook
from pafy.backend_youtube_dl import YtdlPafy

from app.data import VideoStreamObject
from app.util import clip_text, color_tuple_to_int, load_pickle, save_pickle
from app.youtube import get_avatar

logging = getLogger(__name__)


def send_webhook(
    video: YtdlPafy, thumbnail_path: str, avatar_url: str, webhook_url: str
):
    from app.config import webhook_text_max_length

    webhook = DiscordWebhook(url=webhook_url)

    embed = DiscordEmbed()
    embed.set_url(video.watchv_url)
    embed.set_color(color_tuple_to_int(ColorThief(thumbnail_path).get_color(quality=1)))
    embed.set_title(video.title)
    embed.set_description(clip_text(video.description, webhook_text_max_length()))
    embed.set_author(
        name=video.author,
        url=f"https://www.youtube.com/user/{video.username}",
        icon_url=avatar_url,
    )
    embed.set_timestamp(dateutil.parser.parse(video.published).isoformat())
    embed.set_thumbnail(
        url=video.bigthumbhd, width=480, height=360
    )  # clicking "thumbnail" links to the video whereas set_image links to the image file
    # embed.set_image(url=video.bigthumbhd, width=480, height=360)
    embed.set_footer(text=f"Duration: {video.duration}")

    webhook.add_embed(embed)
    webhook.execute()


def process_discord(obj: VideoStreamObject):
    from app.config import webhook_url_list

    video, thumbnail = obj.video, obj.thumbnail
    logging.debug(
        f"Processing Discord WebHook message for '{video.title}'. Video thumbnail is located at '{thumbnail}'."
    )

    avatar_url = get_avatar(video.username)

    for webhook_url in webhook_url_list():
        logging.debug(
            f"Sending Discord WebHook for '{video.title}' to the following Discord WebHook url: {webhook_url}"
        )
        send_webhook(video, thumbnail, avatar_url, webhook_url)

    logging.info(f"Successfully sent Discord WebHook for '{video.title}'")


def is_discord_enabled(obj: VideoStreamObject) -> bool:
    from app.config import webhook_enabled

    if not webhook_enabled():
        logging.info(
            f'Discord WebHook posting not enabled. Skipping sending "{obj.video.title}" to Discord.'
        )
        return False
    return True


def should_post(obj: VideoStreamObject) -> bool:
    from app.config import webhook_posted_pickle_path

    posted_set: Set[str] = load_pickle(
        webhook_posted_pickle_path(), get_default=lambda: set([])
    )
    if obj.id in posted_set:
        logging.debug(
            f"'{obj.video.title}' has already been posted to Discord. Ignoring."
        )
        return False
    logging.debug(f"'{obj.video.title}' has not already been posted to Discord.")
    return True


def init_discord(events: rx.Observable):
    return events.pipe(
        rx.operators.filter(is_discord_enabled), rx.operators.filter(should_post)
    ).subscribe(process_discord)
