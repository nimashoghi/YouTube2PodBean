import asyncio
from datetime import datetime

import dateutil.parser
from colorthief import ColorThief
from discord_webhook import DiscordEmbed, DiscordWebhook
from pafy.backend_youtube_dl import YtdlPafy

from app.util import (
    clip_text,
    color_tuple_to_int,
    download_thumbnail,
    get_avatar,
    is_already_posted,
    load_pickle,
    mark_as_posted,
    new_video_event_handler,
    run_sync,
    save_pickle,
    setup_logging,
    temporary_files,
)

logging = setup_logging("app.services.discord")


async def send_webhook(video: YtdlPafy, color: int, avatar_url: str, webhook_url: str):
    from app.config.discord import webhook_text_max_length

    webhook_text_max_length = await webhook_text_max_length()

    def sync():
        logging.debug(
            f"Sending Discord WebHook for '{video.title}' to the following Discord WebHook url: {webhook_url}"
        )

        webhook = DiscordWebhook(url=webhook_url)

        embed = DiscordEmbed()
        embed.set_url(video.watchv_url)
        embed.set_color(color)
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


async def get_thumbnail_primary_color(video: YtdlPafy):
    logging.debug(f"Downloading thumbnail for video '{video.title}'...")
    thumbnail_path = await download_thumbnail(video)
    logging.debug(
        f"Downloaded thumbnail for video '{video.title}' into '{thumbnail_path}'"
    )
    with temporary_files(thumbnail_path):
        return color_tuple_to_int(ColorThief(thumbnail_path).get_color(quality=1))


async def process_discord(video: YtdlPafy):
    from app.config.discord import webhook_url_list

    thumbnail_color = await get_thumbnail_primary_color(video)

    avatar_url = await get_avatar(video.username)
    logging.debug(
        f"Processing Discord WebHook message for '{video.title}'. Video thumbnail color is '{thumbnail_color:02x}'. Avatar url is '{avatar_url}'."
    )

    await asyncio.gather(
        *(
            send_webhook(video, thumbnail_color, avatar_url, webhook_url)
            for webhook_url in await webhook_url_list()
        )
    )

    logging.info(f"Successfully sent Discord WebHook for '{video.title}'")


async def is_video_too_old(video: YtdlPafy):
    from app.config.discord import webhook_max_duration

    max_duration = await webhook_max_duration()
    return max_duration != 0 and (
        (datetime.now() - dateutil.parser.parse(video.published)).total_seconds()
        > max_duration
    )


if __name__ == "__main__":

    @new_video_event_handler("new_video/discord", logger=logging)
    async def on_new_video(video: YtdlPafy):
        from app.config.discord import webhook_enabled
        from app.config.pickle import webhook_posted_pickle_path

        [enabled, too_old, already_posted] = await asyncio.gather(
            webhook_enabled(),
            is_video_too_old(video),
            is_already_posted(video.videoid, webhook_posted_pickle_path),
        )

        if not enabled:
            logging.info(
                f'Discord WebHook posting not enabled. Skipping sending "{video.title}" to Discord.'
            )
            return
        if too_old:
            logging.info(
                f"Video '{video.title}' is too old to upload to Discord. Skipping."
            )
            return
        if already_posted:
            logging.info(
                f"'{video.title}' has already been posted to Discord. Ignoring."
            )
            return

        logging.info(f"'{video.title}' has not been posted to Discord. Posting.")

        await process_discord(video)
        await mark_as_posted(video.videoid, webhook_posted_pickle_path)
