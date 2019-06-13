import asyncio
from datetime import datetime
from logging import getLogger

import aio_pika as pika
import dateutil.parser
from colorthief import ColorThief
from discord_webhook import DiscordEmbed, DiscordWebhook
from pafy.backend_youtube_dl import YtdlPafy

from app.util import (
    clip_text,
    color_tuple_to_int,
    download_thumbnail,
    get_avatar,
    get_videos,
    load_pickle,
    run_sync,
    save_pickle,
    setup_logging,
)

logging = getLogger(__name__)


async def send_webhook(
    video: YtdlPafy, thumbnail_path: str, avatar_url: str, webhook_url: str
):
    from app.config.discord import webhook_text_max_length

    webhook_text_max_length = await webhook_text_max_length()

    def sync():
        logging.debug(
            f"Sending Discord WebHook for '{video.title}' to the following Discord WebHook url: {webhook_url}"
        )

        webhook = DiscordWebhook(url=webhook_url)

        embed = DiscordEmbed()
        embed.set_url(video.watchv_url)
        embed.set_color(
            color_tuple_to_int(ColorThief(thumbnail_path).get_color(quality=1))
        )
        embed.set_title(video.title)
        embed.set_description(clip_text(video.description, webhook_text_max_length))
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

    return await run_sync(sync)


async def process_discord(video: YtdlPafy):
    from app.config.discord import webhook_url_list

    thumbnail = await download_thumbnail(video)
    logging.debug(f"Downloaded thumbnail for video '{video.title}' into '{thumbnail}'")

    avatar_url = await get_avatar(video.username)
    logging.debug(
        f"Processing Discord WebHook message for '{video.title}'. Video thumbnail is located at '{thumbnail}'. Avatar url is '{avatar_url}'."
    )

    await asyncio.gather(
        *(
            send_webhook(video, thumbnail, avatar_url, webhook_url)
            for webhook_url in await webhook_url_list()
        )
    )

    logging.info(f"Successfully sent Discord WebHook for '{video.title}'")


async def is_already_posted(id: str) -> bool:
    from app.config.pickle import webhook_posted_pickle_path

    posted_set = await load_pickle(
        await webhook_posted_pickle_path(), get_default=lambda: set([])
    )
    return id in posted_set


async def mark_as_posted(id: str):
    from app.config.pickle import webhook_posted_pickle_path

    webhook_posted_pickle_path = await webhook_posted_pickle_path()
    post_history = await load_pickle(
        webhook_posted_pickle_path, get_default=lambda: set([])
    )
    await save_pickle(webhook_posted_pickle_path, set([id, *post_history]))


async def is_video_too_old(video: YtdlPafy):
    from app.config.discord import webhook_max_duration

    max_duration = await webhook_max_duration()
    return max_duration != 0 and (
        (datetime.now() - dateutil.parser.parse(video.published)).total_seconds()
        > max_duration
    )


async def main():
    from app.config.core import message_broker
    from app.config.discord import webhook_enabled

    await asyncio.sleep(5)  # sleep 5s to wait for rabbitmq server to go up

    connection: pika.Connection = await pika.connect_robust(
        await message_broker(), loop=asyncio.get_event_loop()
    )
    async with connection:
        async for video in get_videos(connection):
            [enabled, too_old, already_posted] = await asyncio.gather(
                webhook_enabled(),
                is_video_too_old(video),
                is_already_posted(video.videoid),
            )

            if not enabled:
                logging.info(
                    f'Discord WebHook posting not enabled. Skipping sending "{video.title}" to Discord.'
                )
                continue
            if too_old:
                logging.info(
                    f"Video '{video.title}' is too old to upload to Discord. Skipping."
                )
                continue
            if already_posted:
                logging.info(
                    f"'{video.title}' has already been posted to Discord. Ignoring."
                )
                continue

            logging.info(f"'{video.title}' has not been posted to Discord. Posting.")

            await process_discord(video)
            await mark_as_posted(video.videoid)


if __name__ == "__main__":
    setup_logging("app.services.discord")
    asyncio.run(main())
