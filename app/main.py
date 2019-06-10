import logging
import mimetypes
import multiprocessing as mp
import os
import time
from typing import Callable

import pafy
import requests
from oauthlib.oauth2.rfc6749.errors import (InvalidGrantError,
                                            InvalidTokenError,
                                            TokenExpiredError)
from requests_oauthlib import OAuth2Session

from app.config import client_id, client_secret, port, public_host
from app.detect import detect_videos, process_new_video
from app.server import get_oauth_code as get_oauth_code_from_server
from app.util import load_pickle, save_pickle
from app.webhooks import process_webhooks
from app.wordpress import post_video

redirect_uri = f"http://{public_host()}:{port()}"
scope = ["podcast_read", "podcast_update", "episode_read", "episode_publish"]

oauth_url = "https://api.podbean.com/v1/dialog/oauth"
token_url = "https://api.podbean.com/v1/oauth/token"

authorize_upload_url = "https://api.podbean.com/v1/files/uploadAuthorize"
publish_episode_url = "https://api.podbean.com/v1/episodes"


def authorize_upload(access_token: str, file_path: str):
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


def upload_file(file_path: str, presigned_url: str):
    r = requests.put(
        presigned_url,
        headers={"Content-Type": mimetypes.guess_type(file_path)[0] or "audio/mpeg"},
        data=open(file_path, "rb"),
    )
    if not r.ok:
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


def refresh_access_token(oauth: OAuth2Session):
    from app.config import access_code_pickle_path

    token_info = load_pickle(access_code_pickle_path())
    new_token_info = oauth.refresh_token(
        token_url=token_url, refresh_token=token_info["refresh_token"]
    )
    token_info.update(new_token_info)
    save_pickle(access_code_pickle_path(), token_info)


def get_access_token(oauth: OAuth2Session):
    from app.config import access_code_pickle_path

    return load_pickle(access_code_pickle_path())["access_token"]


def ensure_has_oauth_token(oauth: OAuth2Session):
    from app.config import access_code_pickle_path

    def first_time_auth():
        authorization_url, _ = oauth.authorization_url(oauth_url)
        logging.critical(f"Please visit the link below:\n{authorization_url}")
        code = get_oauth_code_from_server()
        return oauth.fetch_token(
            token_url=token_url,
            code=code,
            client_id=client_id(),
            client_secret=client_secret(),
        )

    load_pickle(access_code_pickle_path(), get_default=first_time_auth)


def main():
    from app.config import enabled, polling_rate, start_from, videos

    while not enabled():
        logging.critical(
            "Application is not enabled (kill switch)... Checking again in 5 seconds."
        )
        time.sleep(5.0)

    oauth = OAuth2Session(client_id=client_id(), redirect_uri=redirect_uri, scope=scope)
    ensure_has_oauth_token(oauth)

    def video_found(video, title, description, mp3, jpg, new, mark_as_processed):
        if new:
            process_webhooks(video, jpg)
            post_video(video)

        while True:
            try:
                access_token = get_access_token(oauth)
                logging.debug(f"PodBean access token is {access_token}.")

                logging.info(f"Uploading '{title}' to PodBean...")
                upload_and_publish_episode(
                    access_token, title, description, video_path=mp3, thumbnail_path=jpg
                )
                logging.info(f"Successfully uploaded '{title}' to PodBean...")

                logging.debug(f"Removing '{mp3}'")
                logging.debug(f"Removing '{jpg}'")
                os.remove(mp3)
                os.remove(jpg)
                logging.info(
                    f"Removed mp3 and jpg files for '{title}' from tmp directory..."
                )
            except (InvalidGrantError, TokenExpiredError, InvalidTokenError):
                logging.info(
                    f"Token expired while trying to upload {video.id}... refreshing"
                )
                refresh_access_token(oauth)
            else:
                mark_as_processed()
                logging.debug(
                    f"Marked '{video}' as successfully processed so we don't check it again."
                )
                break

    process_video_callback = process_new_video(video_found, new=False)
    process_new_video_callback = process_new_video(video_found, new=True)

    start_from_all = start_from()
    logging.info(f"Processing all videos, starting from {start_from_all}...")
    detect_videos(process_video_callback, new_only=False, start_from=start_from_all)

    while True:
        logging.info("Processing manual videos...")
        for id in videos():
            logging.info(f"Processing '{id}'")
            process_video_callback(pafy.new(id))

        start_from_new = start_from()
        logging.info(f"Processing new videos, start from {start_from_new}...")
        detect_videos(process_new_video_callback, start_from=start_from_new)

        wait_time = polling_rate()
        logging.debug(f"Waiting for {wait_time} seconds until next iteration.")
        time.sleep(wait_time)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    mp.freeze_support()

    main()
