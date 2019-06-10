import logging
import re
import tempfile
import time
from collections import OrderedDict
from itertools import chain, islice

import dateutil
import pafy
import requests
import xmltodict

from app.download import download_to_path
from app.util import load_pickle, sanitize_title, save_pickle


def is_valid_title(title):
    from app.config import title_pattern, title_negative_pattern

    return re.search(title_pattern(), title, re.IGNORECASE) is not None and (
        not title_negative_pattern()
        or re.search(title_negative_pattern(), title, re.IGNORECASE) is None
    )


def download_thumbnail(video, title):
    url = video.bigthumbhd if video.bigthumbhd else video.bigthumb

    def get_url_extension(url, default="jpg"):
        import re

        match = re.search(url, r"\.(.+)\s*$")
        return match[1] if match else default

    logging.info(
        f"Downloading thumbnail of '{video.title}' (sanitizied = '{title}') from {url}"
    )

    _, path = tempfile.mkstemp(prefix=title, suffix=f".{get_url_extension(url)}")
    return download_to_path(url, path)


def download_youtube_audio(video, title):
    best = video.getbestaudio(preftype="m4a")

    logging.info(
        f"Downloading audio stream of '{video.title}' (sanitizied = '{title}') from {best.url}"
    )

    _, path = tempfile.mkstemp(prefix=title, suffix=f".{best.extension}")
    return download_to_path(best.url, path)


def mark_as_processed(video):
    from app.config import processed_pickle_path

    processed = load_pickle(processed_pickle_path(), get_default=lambda: set([]))
    save_pickle(processed_pickle_path(), set([video.videoid, *processed]))

    logging.info(f"Added '{video.title}' to list of processed videos.")


def is_processed(video):
    from app.config import processed_pickle_path

    processed = load_pickle(processed_pickle_path(), get_default=lambda: set([]))
    return video.videoid in processed


def process_new_video(callback, new=False):
    def process(video):
        if is_processed(video):
            return False

        title = sanitize_title(video.title)

        mp3_path = download_youtube_audio(video, title)
        thumbnail_path = download_thumbnail(video, title)

        callback(
            video,
            video.title,
            video.description,
            mp3_path,
            thumbnail_path,
            new,
            lambda video=video: mark_as_processed(video),
        )

        return True

    return process


def get_upload_info():
    from app.config import channel_id

    channel_id = channel_id()

    if channel_id[1] == "C":
        return channel_id, f"{channel_id[:1]}U{channel_id[2:]}"
    else:
        return None, channel_id


def get_uploads_from_xml_feed(channel_id):
    entries = xmltodict.parse(
        requests.get(
            f"https://www.youtube.com/feeds/videos.xml",
            params=dict(channel_id=channel_id),
        ).text
    )["feed"]["entry"]

    return [pafy.new(entry["yt:videoId"]) for entry in entries]


def get_all_uploads_updated():
    channel_id, playlist_id = get_upload_info()
    playlist = pafy.get_playlist2(playlist_id)
    xml_playlist = get_uploads_from_xml_feed(channel_id) if channel_id else []

    return OrderedDict(
        (video.videoid, video)
        for video in sorted(
            (video for video in chain(playlist, xml_playlist)),
            key=lambda video: dateutil.parser.parse(video.published),
        )
    ).values()


def get_all_uploads(refetch_latest=0):
    from app.config import playlist_history_pickle_path

    new_playlist = get_all_uploads_updated()

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


def check_start_from(videos, start_from):
    if not start_from:
        yield from videos
    else:
        for video in videos:
            yield video
            if video.videoid == start_from:
                logging.info(f"Video start point set to '{video.title}'")
                break


def detect_videos(f, new_only=True, start_from=None):
    from app.config import video_process_delay, youtube_enabled

    if not youtube_enabled():
        logging.info("YouTube polling not enabled. Skipping current loop")
        return

    new_vidoes, all_videos = get_all_uploads()
    videos = reversed(
        [
            video
            for video in check_start_from(
                all_videos if not new_only else new_vidoes, start_from
            )
            if is_valid_title(video.title)
        ]
    )

    for video in videos:
        if not f(video):
            continue

        delay = video_process_delay()
        logging.info(
            f"Finished processing {video.title}. Waiting for {delay} seconds before processing next video."
        )
        time.sleep(delay)
