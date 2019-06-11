import os
import os.path
import random
import re
import string
import tempfile
import time
from collections import OrderedDict
from itertools import chain, islice
from logging import getLogger

import pafy
import requests

from app.download import download_to_path
from app.util import load_pickle, sanitize_title, save_pickle

logging = getLogger(__name__)


def is_valid_title(title):
    from app.config import title_pattern, title_negative_pattern

    return re.search(title_pattern(), title, re.IGNORECASE) is not None and (
        not title_negative_pattern()
        or re.search(title_negative_pattern(), title, re.IGNORECASE) is None
    )


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


def get_all_uploads(refetch_latest=0):
    def get_playlist_id():
        from app.config import channel_id

        channel_id = channel_id()
        return (
            f"{channel_id[:1]}U{channel_id[2:]}" if channel_id[1] == "C" else channel_id
        )

    from app.config import playlist_history_pickle_path

    playlist_id = get_playlist_id()
    new_playlist = pafy.get_playlist2(playlist_id)

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


def check_api_key():
    from app.config import youtube_api_key

    logging.debug("Checking YouTube API key...")
    api_key = youtube_api_key()
    if api_key:
        pafy.set_api_key(api_key)
        logging.debug(f"Using API key '{api_key}' from config.")
    else:
        logging.debug("No YouTube API key set. Using pafy's default API key.")


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
