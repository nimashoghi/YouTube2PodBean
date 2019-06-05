scope = ["podcast_read", "podcast_update", "episode_read", "episode_publish"]

oauth_url = "https://api.podbean.com/v1/dialog/oauth"
token_url = "https://api.podbean.com/v1/oauth/token"

authorize_upload_url = "https://api.podbean.com/v1/files/uploadAuthorize"
publish_episode_url = "https://api.podbean.com/v1/episodes"


def redirect_uri():
    from app.config import public_host, port

    return f"http://{public_host()}:{port()}"


import asyncio
import mimetypes
import os.path
from typing import Any, Callable, Tuple

import requests
from pafy.backend_youtube_dl import YtdlPafy
from requests_oauthlib import OAuth2Session

from app.config import client_id, client_secret, port, public_host
from app.logging import create_logger
from app.server import get_oauth_code as get_oauth_code_from_server
from app.sync import asyncify

logger, log = create_logger(__name__)


def authorize_upload(access_token: str, file_path: str):
    result = requests.get(
        authorize_upload_url,
        params=dict(
            access_token=access_token,
            filename=os.path.basename(file_path),
            filesize=os.path.getsize(file_path),
            content_type=mimetypes.guess_type(file_path)[0] or "audio/mpeg",
        ),
    ).json()

    try:
        return result["presigned_url"], result["file_key"]
    except BaseException as e:
        print(f"Failed to authoriez upload: {result}")
        raise e


def upload_file(file_path: str, presigned_url: str):
    r = requests.put(
        presigned_url,
        headers={"Content-Type": mimetypes.guess_type(file_path)[0] or "audio/mpeg"},
        data=open(file_path, "rb"),
    )
    if not r.ok:
        raise Exception("Failed to upload")


async def publish_episode(
    access_token: str,
    title: str,
    description: str,
    file_key: str,
    thumbnail_file_key: str,
    status="publish",
    type="public",
) -> Any:
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
    result = response.json()

    try:
        return result["episode"]
    except BaseException as e:
        print(f"Failed to publish episode: {result}")
        raise e


async def authorize_and_upload(access_token: str, file_path: str) -> str:
    presigned_url, file_key = await authorize_upload(access_token, file_path)
    await upload_file(file_path, presigned_url)
    return file_key


async def upload_and_publish_episode(
    access_token: str,
    title: str,
    description: str,
    audio_path: str,
    thumbnail_path: str,
) -> Any:
    from app.config import podbean_enabled

    if not podbean_enabled():
        return

    (audio_key, thumbnail_key, _), _ = await asyncio.wait(
        {
            authorize_and_upload(access_token, audio_path),
            authorize_and_upload(access_token, thumbnail_path),
        }
    )

    return await publish_episode(
        access_token, title, description, audio_key.result(), thumbnail_key.result()
    )


async def refresh_access_token(oauth: OAuth2Session) -> None:
    from app.config import access_code_pickle_path
    from app.util import load_pickle, save_pickle

    @asyncify
    def refresh_token(oauth: OAuth2Session, token_url, refresh_token=None) -> Any:
        return oauth.refresh_token(token_url, refresh_token)

    token_info = await load_pickle(access_code_pickle_path())
    new_token_info = await refresh_token(oauth, token_url, token_info["refresh_token"])
    token_info.update(new_token_info)
    save_pickle(access_code_pickle_path(), token_info)


async def get_access_token(oauth: OAuth2Session) -> str:
    from app.config import access_code_pickle_path
    from app.util import load_pickle

    pickle = await load_pickle(access_code_pickle_path())
    return pickle["access_token"]


@log
async def ensure_has_oauth_token(
    oauth: OAuth2Session, *, logger=logger
) -> OAuth2Session:
    from app.config import access_code_pickle_path
    from app.util import load_pickle

    @asyncify
    def authorization_url(oauth: OAuth2Session, oauth_url: str) -> str:
        return oauth.authorization_url(oauth_url)[0]

    @asyncify
    def fetch_token(
        oauth: OAuth2Session,
        token_url: str,
        code: str,
        client_id: str,
        client_secret: str,
    ) -> Any:
        return oauth.fetch_token(
            token_url=token_url,
            code=code,
            client_id=client_id,
            client_secret=client_secret,
        )

    async def first_time_auth() -> Any:
        logger.info("Handling first time PodBean authentication")

        print(
            f"Please visit the link below:\n{await authorization_url(oauth, oauth_url)}"
        )
        code = await get_oauth_code_from_server()
        return await fetch_token(oauth, token_url, code, client_id(), client_secret())

    await load_pickle(access_code_pickle_path(), get_default=first_time_auth)
    return oauth


async def initialize_oauth_session() -> OAuth2Session:
    from app.config import client_id

    return await ensure_has_oauth_token(
        OAuth2Session(client_id=client_id(), redirect_uri=redirect_uri(), scope=scope)
    )


@log
async def post_to_podbean(
    video: YtdlPafy,
    audio_path: str,
    thumbnail_path: str,
    oauth: OAuth2Session,
    *,
    logger=logger,
) -> None:
    from os import remove

    from oauthlib.oauth2.rfc6749.errors import (
        InvalidGrantError,
        TokenExpiredError,
        InvalidTokenError,
    )

    logger.debug(f"Attempting to upload '{video.title}' to PodBean")

    while True:
        try:
            logger.info(f"\nUploading {video.title} to PodBean...")
            await upload_and_publish_episode(
                await get_access_token(oauth),
                video.title,
                video.description,
                audio_path=audio_path,
                thumbnail_path=thumbnail_path,
            )
            remove(audio_path)
            remove(thumbnail_path)
            logger.info(f"\nUploaded {video.title} to PodBean")
            break
        except (InvalidGrantError, TokenExpiredError, InvalidTokenError):
            print("Token expired... refreshing")
            refresh_access_token(oauth)
