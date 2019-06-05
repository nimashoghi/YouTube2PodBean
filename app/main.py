import asyncio
from typing import AsyncIterable

import pafy
from pafy.backend_youtube_dl import YtdlPafy
from requests_oauthlib import OAuth2Session

from app.logging import create_logger
from app.podbean import initialize_oauth_session

logger, log = create_logger(__name__)


async def process_video(video: YtdlPafy, *, new: bool, oauth: OAuth2Session) -> None:
    from app.download import download_video
    from app.discord import post_to_discord
    from app.wordpress import post_to_wordpress
    from app.podbean import post_to_podbean

    audio_path, thumbnail_path = await download_video(video)

    tasks = []

    if new:
        tasks.append(asyncio.create_task(post_to_discord(video, thumbnail_path)))
        tasks.append(asyncio.create_task(post_to_wordpress(video)))

    tasks.append(
        asyncio.create_task(post_to_podbean(video, audio_path, thumbnail_path, oauth))
    )

    await asyncio.wait(tasks)


queue: asyncio.Queue = asyncio.Queue()


async def get_videos() -> AsyncIterable[YtdlPafy]:
    global queue

    while True:
        yield await queue.get()


async def get_custom_videos() -> AsyncIterable[YtdlPafy]:
    from app.config import videos

    for id in videos():
        yield pafy.new(id)


@log
async def custom_video_processor(oauth: OAuth2Session, *, logger=logger):
    while True:
        async for video in get_custom_videos():
            await process_video(video)
        await asyncio.sleep(5.0)


@log
async def youtube_poller(*, logger=logger):
    return


@log
async def video_processor(oauth: OAuth2Session, *, logger=logger):
    async for video in get_videos():
        await process_video(video)


@log
async def main(*, logger=logger):
    from app.config import enabled

    while not enabled():
        logger.critical("Application is not enabled... Checking again in 5 seconds.")
        await asyncio.sleep(5.0)

    oauth = await initialize_oauth_session()


if __name__ == "__main__":
    import logging
    from multiprocessing import freeze_support

    logging.basicConfig(level=logging.INFO)

    freeze_support()

    asyncio.run(main())
