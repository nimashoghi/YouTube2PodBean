import asyncio
import os
import random
import string
import tempfile
from logging import getLogger

import pafy.g
import youtube_dl.downloader.http
from pafy.backend_youtube_dl import YtdlPafy

from app.util.asyncio import run_sync
from app.util.misc import get_url_extension, sanitize_title, temporary_files

logging = getLogger(__name__)


def strip_extension(path: str):
    return "".join(os.path.splitext(path)[:-1])


async def make_temp_file(
    prefix: str,
    suffix: str,
    directory: str = f"{tempfile.gettempdir()}/youtube2podbean",
) -> str:
    def sync():
        if not os.path.isdir(directory):
            os.mkdir(directory)
        random_string = "".join(random.choice(string.ascii_lowercase) for _ in range(6))
        return f"{directory}/{prefix}{random_string}{suffix}"

    return await run_sync(sync)


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


async def download_to_path(url: str, path: str) -> str:
    def sync():
        downloader = youtube_dl.downloader.http.HttpFD(
            ydl(), {"http_chunk_size": 10_485_760}
        )

        downloader.download(path, dict(url=url))

        return path

    return await run_sync(sync)


async def download_thumbnail(video: YtdlPafy) -> str:
    title = sanitize_title(video.title)
    url = video.bigthumbhd if video.bigthumbhd else video.bigthumb

    path = await make_temp_file(prefix=f"{title}-", suffix=f".{get_url_extension(url)}")
    logging.debug(
        f"Downloading thumbnail of '{video.title}' (sanitizied = '{title}') from '{url}' into '{path}'"
    )
    path = await download_to_path(url, path)
    logging.info(
        f"Downloaded thumbnail of '{video.title}' (sanitizied = '{title}') from '{url}' into '{path}'"
    )

    return path


async def download_audio(video: YtdlPafy) -> str:
    title = sanitize_title(video.title)
    best = video.getbestaudio(preftype="m4a")

    path = await make_temp_file(prefix=f"{title}-", suffix=f".{best.extension}")
    logging.debug(
        f"Downloading audio stream of '{video.title}' (sanitizied = '{title}') from '{best.url}' into '{path}'"
    )
    path = await download_to_path(best.url, path)
    logging.info(
        f"Downloaded audio stream of '{video.title}' (sanitizied = '{title}') from '{best.url}' into '{path}'"
    )

    return path


class VideoConversionException(Exception):
    pass


async def convert_video(path: str):
    output_path = f"{strip_extension(path)}.mp3"

    # call ffmpeg and wait for it to finish
    process = await asyncio.create_subprocess_exec(
        "ffmpeg", "-i", path, "-ac", "2", "-ab", "128000", "-ar", "44100", output_path
    )

    return_code = await process.wait()

    if return_code != 0:
        stdout, stderr = await process.communicate()
        raise VideoConversionException(
            f"Failed to convert video located at {path}.\nStdout: {stdout}\nStderr: {stderr}"
        )
    return output_path


async def download_audio_as_mp3(video: YtdlPafy) -> str:
    original_audio = await download_audio(video)
    with temporary_files(original_audio):
        return await convert_video(original_audio)
