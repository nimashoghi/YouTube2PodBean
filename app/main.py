import mimetypes
import multiprocessing as mp
import os
import time
from datetime import datetime
from logging import getLogger
from typing import Callable

import pafy
import requests
from oauthlib.oauth2.rfc6749.errors import (
    InvalidGrantError,
    InvalidTokenError,
    TokenExpiredError,
)
from pafy.backend_youtube_dl import YtdlPafy
from requests_oauthlib import OAuth2Session

from app.detect import check_api_key, detect_videos, process_new_video
from app.modules.discord import process_webhooks
from app.modules.podbean import add_to_podbean, init_podbean
from app.modules.wordpress import post_video
from app.server import get_oauth_code as get_oauth_code_from_server

logging = getLogger(__name__)


def wait_for_enabled():
    from app.config import enabled

    while not enabled():
        logging.critical(
            "Application is not enabled (kill switch)... Checking again in 5 seconds."
        )
        time.sleep(5.0)
    logging.info(f"Application is enabled. Staritng...")


def video_found(
    video: YtdlPafy,
    audio_path: str,
    thumbnail_path: str,
    is_new: bool,
    mark_as_processed: Callable,
):
    logging.debug(
        f"Processing video = '{video}';\n title = '{video.title}';\n description = '{video.description}';\n audio_path = '{audio_path}';\n thumbnail_path = '{thumbnail_path}';\n is_new = '{is_new}'"
    )

    if is_new:
        logging.info(
            f"Video '{video.title}' is a new video. Uploading to WordPress and posting to Discord."
        )

        process_webhooks(video, thumbnail_path)
        post_video(video)

    try:
        add_to_podbean(video, audio_path, thumbnail_path)
    except:
        pass
    else:
        mark_as_processed()
        logging.debug(
            f"Marked '{video.title}' as successfully processed so we don't check it again."
        )
    finally:
        logging.debug(f"Removing '{audio_path}'")
        os.remove(audio_path)

        logging.debug(f"Removing '{thumbnail_path}'")
        os.remove(thumbnail_path)

        logging.info(
            f"Removed audio_path and thumbnail_path files for '{video.title}' from tmp directory..."
        )


def main():
    from app.config import client_id, enabled, manual_videos, polling_rate, start_from

    # wait for config enabled setting to be on (kill switch)
    wait_for_enabled()

    init_podbean()

    process_video_callback = process_new_video(video_found, new=False)
    process_new_video_callback = process_new_video(video_found, new=True)

    check_api_key()

    start_from_all = start_from()
    logging.info(
        f"Processing all videos... " + f"Video start point set to {start_from_all}."
        if start_from_all
        else "No video start point set"
    )
    detect_videos(process_video_callback, new_only=False, start_from=start_from_all)

    while True:
        check_api_key()

        logging.info("Processing manual videos...")
        unprocessed_videos = []
        for id in manual_videos():
            video = pafy.new(id)
            try:
                logging.info(f"Processing custom video '{video.title}'")
                process_video_callback(video)
            except:
                logging.error(
                    f"Failed to process custom video '{video.title}'. Retrying the video in the next iteration."
                )
                unprocessed_videos.append(id)
        manual_videos(unprocessed_videos)  # failed videos get retried

        start_from_new = start_from()
        logging.info(
            f"Processing new videos... " + f"Video start point set to {start_from_new}."
            if start_from_new
            else "No video start point set"
        )
        detect_videos(process_new_video_callback, start_from=start_from_new)

        wait_time = polling_rate()
        logging.debug(f"Waiting for {wait_time} seconds until next iteration.")
        time.sleep(wait_time)


def setup_logging():
    import logging as logging_

    log_filename = f"./logs/youtube2podbean-{time.strftime('%Y%m%d-%H%M%S')}.log"
    # log to both stderr and a file
    logging_.basicConfig(
        level=logging_.DEBUG,
        handlers=[logging_.FileHandler(log_filename), logging_.StreamHandler()],
    )
    logging.info(f"Logging to '{log_filename}'")


if __name__ == "__main__":
    setup_logging()
    mp.freeze_support()

    try:
        main()
    except BaseException as e:
        logging.exception(
            msg=f"Top-level unhandled exception of type {type(e)}", exc_info=e
        )
        raise e  # reraise
