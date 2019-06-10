import os

import pafy.g
import youtube_dl.downloader.http


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


def download_to_path(url, path):
    downloader = youtube_dl.downloader.http.HttpFD(
        ydl(), {"http_chunk_size": 10_485_760}
    )

    downloader.download(path, dict(url=url))

    return path
