import asyncio
import os
from typing import Tuple

import youtube_dl
from pafy import g
from pafy.backend_youtube_dl import YtdlPafy

from app.logging import create_logger
from app.sync import asyncify

logger, log = create_logger(__name__)


class ydl:
    def urlopen(self, url):
        return g.opener.open(url)

    def to_screen(self, *args, **kwargs):
        pass

    def to_console_title(self, *args, **kwargs):
        pass

    def trouble(self, *args, **kwargs):
        pass

    def report_warning(self, *args, **kwargs):
        pass

    def report_error(self, *args, **kwargs):
        pass


@asyncify
def download_to_path(url, path):
    downloader = youtube_dl.downloader.http.HttpFD(
        ydl(), {"http_chunk_size": 10_485_760}
    )

    downloader.download(path, dict(url=url))

    return path


@log
async def download_thumbnail(video: YtdlPafy, *, logger=logger) -> str:
    from app.download import download_to_path
    from app.util import sanitize_title

    title = sanitize_title(video.title)
    url = video.bigthumbhd if video.bigthumbhd else video.bigthumb

    def get_url_extension(url, default="jpg"):
        import re

        match = re.search(url, r"\.(.+)\s*$")
        return match[1] if match else default

    path = await download_to_path(url, f"/tmp/{title}.{get_url_extension(url)}")
    logger.info(f"Downloading thumbnail for '{title}' from '{url}' into '{path}'")
    return path


@log
async def download_audio(video: YtdlPafy, *, logger=logger) -> str:
    from app.download import download_to_path
    from app.util import sanitize_title

    best = video.getbestaudio(preftype="m4a")

    title = sanitize_title(video.title)
    url = best.url

    path = await download_to_path(url, f"/tmp/{title}.{best.extension}")
    logger.info(f"Downloading audio for '{title}' from '{url}' into '{path}'")
    return path


@log
async def download_video(video: YtdlPafy, *, logger=logger) -> Tuple[str, str]:
    (audio, thumbnail), _ = await asyncio.wait(
        {download_audio(video), download_thumbnail(video)}
    )

    return (audio.result(), thumbnail.result())
