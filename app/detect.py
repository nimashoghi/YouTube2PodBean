import multiprocessing as mp
from asyncio import Queue
from typing import Callable, Iterable, List, Tuple, Union

from pafy.backend_youtube_dl import YtdlPafy

from app.logging import create_logger
from app.util import fetch_text

logger, log = create_logger(__name__)


@log
def is_valid_title(title, *, logger=logger):
    import re
    from app.config import title_pattern, title_negative_pattern

    title_pattern = title_pattern()
    title_negative_pattern = title_negative_pattern()

    if re.search(title_pattern(), title, re.IGNORECASE) is None:
        logger.info(
            f"'{title}' skipped because title doesn't match the include pattern."
        )
        return False
    elif (
        title_negative_pattern
        and re.search(title_negative_pattern(), title, re.IGNORECASE) is not None
    ):
        logger.info(f"'{title}' skipped because title matches the skip pattern.")
        return False
    else:
        logger.debug(f"'{title}' is a valid title.")
        return True


@log
async def is_processed(video: YtdlPafy, *, logger=logger) -> bool:
    from app.config import processed_pickle_path
    from app.util import load_pickle, save_pickle

    path = processed_pickle_path()
    processed = await load_pickle(path, get_default=lambda: set([]))

    if video.videoid in processed:
        logger.debug(f"'{video.title}' is already processed.")
        return True
    else:
        logger.info(f"Adding '{video.title}' to the processed video list.")
        await save_pickle(path, set([video.videoid, *processed]))
        return False


def get_upload_info() -> Tuple[Union[str, None], str]:
    from app.config import channel_id

    channel_id_: str = channel_id()

    if channel_id_[1] == "C":
        return channel_id_, f"{channel_id_[:1]}U{channel_id_[2:]}"
    else:
        return None, channel_id_


@log
async def get_uploads_from_xml_feed(
    channel_id: str, *, logger=logger
) -> List[YtdlPafy]:
    import pafy
    from xmltodict import parse

    text = await fetch_text(
        f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    ).text
    logger.debug(f"Received following XML from feed: {text}")
    return [pafy.new(entry["yt:videoId"]) for entry in parse(text)["feed"]["entry"]]


@log
def get_all_uploads_updated(*, logger=logger) -> List[YtdlPafy]:
    import pafy
    from collections import OrderedDict
    from itertools import chain
    from dateutil import parser

    channel_id, playlist_id = get_upload_info()

    playlist = pafy.get_playlist2(playlist_id)
    xml_playlist = get_uploads_from_xml_feed(channel_id) if channel_id else []

    all_videos = list(
        OrderedDict(
            (video.videoid, video)
            for video in sorted(
                (video for video in chain(playlist, xml_playlist)),
                key=lambda video: parser.parse(video.published),
            )
        ).values()
    )
    logger.debug(f"Most recent uploads: {[video.videoid for video in all_videos]}")
    return all_videos


async def get_all_uploads(refetch_latest=0):
    from itertools import islice
    from app.config import playlist_history_pickle_path
    from app.util import load_pickle, save_pickle

    new_playlist = await get_all_uploads_updated()

    saved_playlist = load_pickle(
        playlist_history_pickle_path(), lambda new_playlist=new_playlist: new_playlist
    )
    old_count = len(saved_playlist) - refetch_latest
    count_difference = max([len(new_playlist) - old_count, 0])

    new_items_in_playlist = [*islice(new_playlist, 0, count_difference)]
    saved_playlist = [
        *new_items_in_playlist,
        *islice(saved_playlist, refetch_latest, len(saved_playlist)),
    ]
    save_pickle(playlist_history_pickle_path(), saved_playlist)

    return new_items_in_playlist, saved_playlist


@log
def check_start_from(
    videos: List[YtdlPafy], start_from: Union[YtdlPafy, None], *, logger=logger
) -> Iterable[YtdlPafy]:
    if not start_from:
        logger.debug("No start from set.")
        yield from videos
    else:
        logger.debug(f"Start from set to '{start_from.title}'")
        for video in videos:
            yield video
            if video.videoid == start_from.videoid:
                logger.info(
                    f'Video start point detected. Checking videos up to "{video.title}".'
                )
                break


@log
def get_relevant_videos(
    new_only=True, start_from: Union[str, None] = None, *, logger=logger
):
    new_items, all_videos = get_all_uploads()
    return reversed(
        [
            video
            for video in check_start_from(
                all_videos if not new_only else new_items, start_from
            )
            if is_valid_title(video.title)
        ]
    )


@log
def detect_videos(
    f: Callable,
    new_only=True,
    start_from: Union[YtdlPafy, None] = None,
    *,
    logger=logger,
) -> None:
    from app.config import video_process_delay, youtube_enabled
    from time import sleep

    if not youtube_enabled():
        logger.info("YouTube polling not enabled. Skipping current loop.")
        return

    new_items, all_videos = get_all_uploads()
    videos = reversed(
        [
            video
            for video in check_start_from(
                all_videos if not new_only else new_items, start_from
            )
            if is_valid_title(video.title)
        ]
    )

    for video in videos:
        if not f(video):
            continue

        delay = video_process_delay()
        print(f"Finished processing {video.title}. Waiting for {delay} seconds")
        sleep(delay)


async def detect_videos_loop(queue: Queue) -> None:
    from asyncio import sleep
    from app.config import polling_rate

    while True:

        await sleep(polling_rate())
