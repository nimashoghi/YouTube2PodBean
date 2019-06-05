import os

import youtube_dl
from pafy import g
from pafy.backend_youtube_dl import YtdlPafy

from app.logging import create_logger

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


def download_to_path(url, path):
    downloader = youtube_dl.downloader.http.HttpFD(
        ydl(), {"http_chunk_size": 10_485_760}
    )

    downloader.download(path, dict(url=url))

    return path


@log
def download_thumbnail(video: YtdlPafy, *, logger=logger) -> str:
    from app.download import download_to_path
    from app.util import sanitize_title

    title = sanitize_title(video.title)
    url = video.bigthumbhd if video.bigthumbhd else video.bigthumb

    def get_url_extension(url, default="jpg"):
        import re

        match = re.search(url, r"\.(.+)\s*$")
        return match[1] if match else default

    path = download_to_path(url, f"/tmp/{title}.{get_url_extension(url)}")
    logger.info(f"Downloading thumbnail for '{title}' from '{url}' into '{path}'")
    return path


def download_youtube_audio(video: YtdlPafy, *, logger=logger) -> str:
    from app.download import download_to_path
    from app.util import sanitize_title

    best = video.getbestaudio(preftype="m4a")

    title = sanitize_title(video.title)
    url = best.url

    path = download_to_path(url, f"/tmp/{title}.{best.extension}")
    logger.info(f"Downloading audio for '{title}' from '{url}' into '{path}'")
    return path
