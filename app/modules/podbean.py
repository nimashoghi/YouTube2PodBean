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

from app.detect import detect_videos, process_new_video
from app.modules.discord import process_webhooks
from app.modules.wordpress import post_video
from app.server import get_oauth_code as get_oauth_code_from_server
from app.util import load_pickle, save_pickle

logging = getLogger(__name__)


def redirect_uri():
    from app.config import port, public_host

    return f"http://{public_host()}:{port()}"


scope = ["podcast_read", "podcast_update", "episode_read", "episode_publish"]

oauth_url = "https://api.podbean.com/v1/dialog/oauth"
token_url = "https://api.podbean.com/v1/oauth/token"

authorize_upload_url = "https://api.podbean.com/v1/files/uploadAuthorize"
publish_episode_url = "https://api.podbean.com/v1/episodes"


oauth: OAuth2Session


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
        raise Exception(
            f"Failed to upload file located at '{file_path}'. Presigned url = '{presigned_url}'. Response text = '{response.text}'"
        )


def publish_episode(
    access_token: str,
    title: str,
    description: str,
    audio_file_key: str,
    thumbnail_file_key: str,
    status="publish",
    type="public",
):
    logging.debug(
        f"Attempting to publish episode '{title}' with audio_file_key='{audio_file_key}' and thumbnail_file_key='{thumbnail_file_key}'."
    )

    response = requests.post(
        publish_episode_url,
        data=dict(
            access_token=access_token,
            title=title,
            content=description[0:500],  # first 500 chars
            status=status,
            type=type,
            media_key=audio_file_key,
            logo_key=thumbnail_file_key,
        ),
    )
    if not response.ok:
        logging.error(
            f"Got an invalid status code from PodBean API servers while trying to publish episdoe '{title}'. status_code='{response.status_code}'. text='{response.text}'."
        )
        return

    result = response.json()

    try:
        episode = result["episode"]
    except BaseException as e:
        logging.error(
            f"Failed to publish episode '{title}' with audio_file_key='{audio_file_key}' and thumbnail_file_key='{thumbnail_file_key}'. Response text = '{result}'."
        )
        raise e
    else:
        logging.debug(
            f"Successfully published '{title}' with audio_file_key='{audio_file_key}' and thumbnail_file_key='{thumbnail_file_key}'."
        )
        return episode


def upload_episode_files(
    access_token: str, audio_path: str, thumbnail_path: str, title: str
):
    logging.debug(f"Attempting to upload episode '{title}'.")

    logging.debug(f"Uploading video for '{title}' located at '{audio_path}'.")
    presigned_url, audio_file_key = authorize_upload(access_token, audio_path)
    upload_file(audio_path, presigned_url)

    logging.debug(f"Uploading thumbnail for '{title}' located at '{thumbnail_path}'.")
    presigned_url, thumbnail_file_key = authorize_upload(access_token, thumbnail_path)
    upload_file(thumbnail_path, presigned_url)

    return (audio_file_key, thumbnail_file_key)


def get_access_token(oauth: OAuth2Session):
    """Tries to get the saved access token and refreshes it if it's expired.

    Arguments:
        oauth {OAuth2Session} -- OAuth client

    Returns:
        str -- the access token
    """
    from app.config import access_code_pickle_path, client_id, client_secret

    pickle_path = access_code_pickle_path()  # pickles/access_code.pickle

    token_info = load_pickle(pickle_path)
    expires_at = datetime.fromtimestamp(token_info["expires_at"])
    logging.debug(
        f"Saved access token in access_code.pickle expires at '{expires_at}'."
    )
    if expires_at <= datetime.now():  # expired?
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

    from app.config import access_code_pickle_path

    load_pickle(access_code_pickle_path(), get_default=first_time_auth)


def init_podbean():
    from app.config import client_id, polling_rate, start_from

    global oauth
    oauth = OAuth2Session(
        client_id=client_id(), redirect_uri=redirect_uri(), scope=scope
    )
    ensure_has_oauth_token(oauth)


def add_to_podbean(video: YtdlPafy, audio_path: str, thumbnail_path: str) -> None:
    """Uploads and publishes a video to Podbean
    """
    from app.config import podbean_enabled

    if not podbean_enabled():
        logging.info(f"PodBean upload not enabled. Skipping uploading '{video.title}'.")
        return

    global oauth
    logging.debug(f"Getting PodBean access token...")
    access_token = get_access_token(oauth)
    logging.debug(f"PodBean access token is '{access_token}'.")

    logging.debug(f"Uploading '{video.title}' to PodBean...")
    audio_file_key, thumbnail_file_key = upload_episode_files(
        access_token,
        audio_path=audio_path,
        thumbnail_path=thumbnail_path,
        title=video.title,
    )
    publish_episode(
        access_token, video.title, video.description, audio_file_key, thumbnail_file_key
    )
    logging.info(f"Successfully uploaded '{video.title}' to PodBean...")
