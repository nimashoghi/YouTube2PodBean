import os
import re
from logging import getLogger

import pafy.g
import youtube_dl.downloader.http
from pafy.backend_youtube_dl import YtdlPafy

from app.util import get_url_extension, make_temp_file

logging = getLogger(__name__)


class ydl:
    def urlopen(self, url):
        return pafy.g.opener.open(url)

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


def download_to_path(url: str, path: str) -> str:
    downloader = youtube_dl.downloader.http.HttpFD(
        ydl(), {"http_chunk_size": 10_485_760}
    )

    downloader.download(path, dict(url=url))

    return path


def download_thumbnail(video: YtdlPafy, title: str) -> str:
    url = video.bigthumbhd if video.bigthumbhd else video.bigthumb

    path = make_temp_file(prefix=f"{title}-", suffix=f".{get_url_extension(url)}")

    logging.debug(
        f"Downloading thumbnail of '{video.title}' (sanitizied = '{title}') from '{url}' into '{path}'"
    )
    path = download_to_path(url, path)
    logging.info(
        f"Downloaded thumbnail of '{video.title}' (sanitizied = '{title}') from '{url}' into '{path}'"
    )

    return path


def download_audio(video: YtdlPafy, title: str) -> str:
    best = video.getbestaudio(preftype="m4a")

    path = make_temp_file(prefix=f"{title}-", suffix=f".{best.extension}")

    logging.debug(
        f"Downloading audio stream of '{video.title}' (sanitizied = '{title}') from '{best.url}' into '{path}'"
    )
    path = download_to_path(best.url, path)
    logging.info(
        f"Downloaded audio stream of '{video.title}' (sanitizied = '{title}') from '{best.url}' into '{path}'"
    )

    return path
