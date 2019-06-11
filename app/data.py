from dataclasses import dataclass

from pafy.backend_youtube_dl import YtdlPafy


@dataclass
class VideoStreamObject:
    id: str
    audio: str
    thumbnail: str
    video: YtdlPafy
