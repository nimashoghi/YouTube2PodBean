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
from requests_oauthlib import OAuth2Session

from app.detect import detect_videos, process_new_video
from app.server import get_oauth_code as get_oauth_code_from_server
from app.util import load_pickle, save_pickle
from app.webhooks import process_webhooks
from app.wordpress import post_video

logging = getLogger(__name__)


def redirect_uri():
    from app.config import port, public_host

    return f"http://{public_host()}:{port()}"


scope = ["podcast_read", "podcast_update", "episode_read", "episode_publish"]

oauth_url = "https://api.podbean.com/v1/dialog/oauth"
token_url = "https://api.podbean.com/v1/oauth/token"

authorize_upload_url = "https://api.podbean.com/v1/files/uploadAuthorize"
publish_episode_url = "https://api.podbean.com/v1/episodes"


def authorize_upload(access_token: str, file_path: str):
    logging.debug(f"Attemping to upload file '{file_path}' to PodBean.")
    result = requests.get(
        authorize_upload_url,
        params=dict(
            access_token=access_token,
            filename=os.path.basename(file_path),
            filesize=str(os.path.getsize(file_path)),
            content_type=mimetypes.guess_type(file_path)[0] or "audio/mpeg",
        ),
    ).json()

    try:
        return result["presigned_url"], result["file_key"]
    except BaseException as e:
        logging.error(f"Failed to authorize upload: {result}")
        raise e
    else:
        logging.debug(f"Successfully uploaded file '{file_path}' to PodBean.")


def upload_file(file_path: str, presigned_url: str):
    response = requests.put(
        presigned_url,
        headers={"Content-Type": mimetypes.guess_type(file_path)[0] or "audio/mpeg"},
        data=open(file_path, "rb"),
    )

    if not response.ok:
        logging.error(
            f"Failed to upload file located at '{file_path}'. Presigned url = '{presigned_url}'"
        )
        raise Exception(
            f"Failed to upload file located at '{file_path}'. Presigned url = '{presigned_url}'"
        )


def publish_episode(
    access_token: str,
    title: str,
    description: str,
    file_key: str,
    thumbnail_file_key: str,
    status="publish",
    type="public",
):
    logging.debug(
        f"Attempting to publish episode '{title}' with file_key='{file_key}' and thumbnail_file_key='{thumbnail_file_key}'."
    )

    response = requests.post(
        publish_episode_url,
        data=dict(
            access_token=access_token,
            title=title,
            content=description[0:500],  # first 500 chars
            status=status,
            type=type,
            media_key=file_key,
            logo_key=thumbnail_file_key,
        ),
    )
    if not response.ok:
        logging.error(
            f"Got an invalid status code from PodBean API servers while trying to publish episdoe '{title}'. status_code={response.status_code}. text={response.text}."
        )
        return

    result = response.json()

    try:
        episode = result["episode"]
    except BaseException as e:
        logging.error(
            f"Failed to publish episode '{title}' with file_key='{file_key}' and thumbnail_file_key='{thumbnail_file_key}'. JSON response: {result}."
        )
        raise e
    else:
        logging.debug(
            f"Successfully published '{title}' with file_key='{file_key}' and thumbnail_file_key='{thumbnail_file_key}'."
        )
        return episode


def upload_and_publish_episode(
    access_token: str,
    title: str,
    description: str,
    video_path: str,
    thumbnail_path: str,
):
    from app.config import podbean_enabled

    logging.debug(f"Attempting to upload and publish episode '{title}'.")

    if not podbean_enabled():
        logging.info(f"PodBean upload not enabled. Skipping uploading '{title}'.")
        return

    logging.debug(f"Uploading video for '{title}' located at '{video_path}'.")
    presigned_url, file_key = authorize_upload(access_token, video_path)
    upload_file(video_path, presigned_url)

    logging.debug(f"Uploading thumbnail for '{title}' located at '{thumbnail_path}'.")
    presigned_url, thumbnail_file_key = authorize_upload(access_token, thumbnail_path)
    upload_file(thumbnail_path, presigned_url)

    return publish_episode(
        access_token, title, description, file_key, thumbnail_file_key
    )


def get_access_token(oauth: OAuth2Session):
    """Tries to get the saved access token and refreshes it if it's expired.

    Arguments:
        oauth {OAuth2Session} -- OAuth client

    Returns:
        str -- the access token
    """
    from app.config import access_code_pickle_path, client_id, client_secret

    pickle_path = access_code_pickle_path()

    token_info = load_pickle(pickle_path)
    expires_at = datetime.fromtimestamp(token_info["expires_at"])
    logging.debug(
        f"Saved access token in access_code.pickle expires at '{expires_at}'."
    )
    if expires_at <= datetime.now():
        logging.info(
            f"Stored access token has expired '{token_info['access_token']}'. Refreshing with refresh token '{token_info['refresh_token']}'..."
        )

        # refresh the token
        new_token_info = oauth.refresh_token(
            token_url=token_url,
            refresh_token=token_info["refresh_token"],
            auth=(client_id(), client_secret()),
        )
        new_token_info["expires_at"] = (
            datetime.timestamp(datetime.now()) + new_token_info["expires_in"]
        )
        token_info.update(new_token_info)

        # save info into pickle
        save_pickle(pickle_path, token_info)
    else:
        logging.debug(f"Access token is not expired.")

    return token_info["access_token"]


def ensure_has_oauth_token(oauth: OAuth2Session):
    from app.config import access_code_pickle_path

    def first_time_auth():
        from app.config import client_id, client_secret

        id = client_id()
        secret = client_secret()

        authorization_url, _ = oauth.authorization_url(oauth_url)
        logging.critical(f"Please visit the link below:\n{authorization_url}")
        code = get_oauth_code_from_server()
        return oauth.fetch_token(
            token_url=token_url,
            code=code,
            auth=(id, secret),
            client_id=id,
            client_secret=secret,
        )

    load_pickle(access_code_pickle_path(), get_default=first_time_auth)


def check_api_key():
    from app.config import youtube_api_key

    api_key = youtube_api_key()
    if api_key:
        pafy.set_api_key(api_key)
        logging.debug(f"Using API key '{api_key}' from config.")
    else:
        logging.debug("No YouTube API key set. Using pafy's default API key.")


def main():
    from app.config import client_id, custom_videos, enabled, polling_rate, start_from

    while not enabled():
        logging.critical(
            "Application is not enabled (kill switch)... Checking again in 5 seconds."
        )
        time.sleep(5.0)

    oauth = OAuth2Session(
        client_id=client_id(), redirect_uri=redirect_uri(), scope=scope
    )
    ensure_has_oauth_token(oauth)

    def video_found(video, title, description, mp3, jpg, new, mark_as_processed):
        logging.debug(
            f"Processing video = '{video}';\n title = '{title}';\n description = '{description}';\n mp3 = '{mp3}';\n jpg = '{jpg}';\n new = '{new}'"
        )

        if new:
            logging.info(
                f"Video '{title}' is a new video. Uploading to WordPress and posting to Discord."
            )

            process_webhooks(video, jpg)
            post_video(video)

        try:
            access_token = get_access_token(oauth)
            logging.debug(f"PodBean access token is '{access_token}'.")

            logging.debug(f"Uploading '{title}' to PodBean...")
            upload_and_publish_episode(
                access_token, title, description, video_path=mp3, thumbnail_path=jpg
            )
            logging.info(f"Successfully uploaded '{title}' to PodBean...")
            mark_as_processed()
            logging.debug(
                f"Marked '{video.title}' as successfully processed so we don't check it again."
            )
        finally:
            logging.debug(f"Removing '{mp3}'")
            os.remove(mp3)

            logging.debug(f"Removing '{jpg}'")
            os.remove(jpg)

            logging.info(
                f"Removed mp3 and jpg files for '{title}' from tmp directory..."
            )

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
        logging.debug("Checking YouTube API key...")
        check_api_key()

        logging.info("Processing manual videos...")
        unprocessed_videos = []
        for id in custom_videos():
            video = pafy.new(id)
            try:
                logging.info(f"Processing custom video '{video.title}'")
                process_video_callback(video)
            except:
                logging.error(
                    f"Failed to process custom video '{video.title}'. Retrying the video in the next iteration."
                )
                unprocessed_videos.append(id)
        custom_videos(unprocessed_videos)  # failed videos get retried

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
