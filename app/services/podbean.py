import asyncio
import mimetypes
import multiprocessing as mp
import os
import re
import time
from ctypes import c_char_p
from datetime import datetime
from logging import getLogger

import aiofiles
import aiohttp
import aiohttp.web
from pafy.backend_youtube_dl import YtdlPafy
from requests_oauthlib import OAuth2Session

from app.util import (
    download_audio,
    download_thumbnail,
    get_videos,
    load_pickle,
    log_exceptions,
    run_sync,
    save_pickle,
    setup_logging,
)

logging = getLogger(__name__)


async def redirect_uri():
    from app.config.server import port, public_host

    [port, public_host] = await asyncio.gather(port(), public_host())
    return f"http://{public_host}:{port}"


scope = ["podcast_read", "podcast_update", "episode_read", "episode_publish"]

oauth_url = "https://api.podbean.com/v1/dialog/oauth"
token_url = "https://api.podbean.com/v1/oauth/token"

authorize_upload_url = "https://api.podbean.com/v1/files/uploadAuthorize"
publish_episode_url = "https://api.podbean.com/v1/episodes"

mp.set_start_method("spawn", True)


def start_oauth_code_server(code, host: str, port: str):
    async def oauth_callback(request: aiohttp.web.Request):
        request_code = request.rel_url.query["code"]
        if not request_code:
            return aiohttp.web.Response(text="Failed to authorize!")
        else:
            code.value = request_code
            return aiohttp.web.Response(text="Successfully authorized!")

    app = aiohttp.web.Application()
    app.router.add_get("/", oauth_callback)
    logging.info(f"Starting OAuth callback server at {host}:{port}")
    aiohttp.web.run_app(app, host=host, port=port)


def get_oauth_code(host: str, port: str):
    manager = mp.Manager()
    code = manager.Value(c_char_p, "")
    server = mp.Process(target=start_oauth_code_server, args=(code, host, port))
    server.start()

    while not code.value:
        time.sleep(0.5)

    server.terminate()
    server.join()

    return code.value


async def is_valid_title(title):
    from app.config.podbean import title_pattern, title_negative_pattern

    [title_pattern, title_negative_pattern] = await asyncio.gather(
        title_pattern(), title_negative_pattern()
    )
    return re.search(title_pattern, title, re.IGNORECASE) is not None and (
        not title_negative_pattern
        or re.search(title_negative_pattern, title, re.IGNORECASE) is None
    )


async def authorize_upload(access_token: str, file_path: str):
    logging.debug(f"Attemping to upload file '{file_path}' to PodBean.")

    async with aiohttp.ClientSession() as session:
        async with session.get(
            url=authorize_upload_url,
            params=dict(
                access_token=access_token,
                filename=os.path.basename(file_path),
                filesize=str(os.path.getsize(file_path)),
                content_type=mimetypes.guess_type(file_path)[0] or "audio/mpeg",
            ),
        ) as response:
            if response.status != 200:
                raise Exception(
                    f"Failed to authorize upload. Access token = '{access_token}'; file path = '{file_path}'; Response text = '{response.text}'"
                )
            result = await response.json()

    try:
        return result["presigned_url"], result["file_key"]
    except BaseException as e:
        logging.error(f"Failed to authorize upload: {result}")
        raise e
    else:
        logging.debug(f"Successfully uploaded file '{file_path}' to PodBean.")


async def upload_file(file_path: str, presigned_url: str):
    async with aiofiles.open(file_path, mode="rb") as f:
        data = await f.read()
        async with aiohttp.ClientSession() as session:
            async with session.put(
                url=presigned_url,
                data=data,
                headers={
                    "Content-Type": mimetypes.guess_type(file_path)[0] or "audio/mpeg"
                },
            ) as response:
                if response.status != 200:
                    raise Exception(
                        f"Failed to upload file located at '{file_path}'. Presigned url = '{presigned_url}'. Response text = '{response.text}'"
                    )
                else:
                    logging.debug(
                        f"Successfully uploaded file '{file_path}' to presigned url '{presigned_url}'."
                    )


async def publish_episode(
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

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url=publish_episode_url,
            data=dict(
                access_token=access_token,
                title=title,
                content=description[0:500],  # first 500 chars
                status=status,
                type=type,
                media_key=audio_file_key,
                logo_key=thumbnail_file_key,
            ),
        ) as response:
            if response.status != 200:
                logging.error(
                    f"Got an invalid status code from PodBean API servers while trying to publish episdoe '{title}'. status='{response.status}'. text='{response.text}'."
                )
                return

            result = await response.json()

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


async def upload_episode_files(
    access_token: str, audio_path: str, thumbnail_path: str, title: str
):
    logging.debug(f"Attempting to upload episode '{title}'.")

    async def upload_audio():
        logging.debug(f"Uploading audio for '{title}' located at '{audio_path}'.")
        presigned_url, audio_file_key = await authorize_upload(access_token, audio_path)
        await upload_file(audio_path, presigned_url)
        return audio_file_key

    async def upload_thumbnail():
        logging.debug(
            f"Uploading thumbnail for '{title}' located at '{thumbnail_path}'."
        )
        presigned_url, thumbnail_file_key = await authorize_upload(
            access_token, thumbnail_path
        )
        await upload_file(thumbnail_path, presigned_url)
        return thumbnail_file_key

    # run the two operations concurrently
    [audio_file_key, thumbnail_file_key] = await asyncio.gather(
        upload_audio(), upload_thumbnail()
    )
    return audio_file_key, thumbnail_file_key


async def get_access_token(oauth: OAuth2Session):
    """Tries to get the saved access token and refreshes it if it's expired.

    Arguments:
        oauth {OAuth2Session} -- OAuth client

    Returns:
        str -- the access token
    """
    from app.config.pickle import access_code_pickle_path
    from app.config.podbean import client_id, client_secret

    [access_code_pickle_path, client_id, client_secret] = await asyncio.gather(
        access_code_pickle_path(), client_id(), client_secret()
    )

    token_info = await load_pickle(access_code_pickle_path)
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
            auth=(client_id, client_secret),
        )
        new_token_info["expires_at"] = (
            datetime.timestamp(datetime.now()) + new_token_info["expires_in"]
        )
        token_info.update(new_token_info)

        # save info into pickle
        await save_pickle(access_code_pickle_path, token_info)
    else:
        logging.debug(f"Access token is not expired.")

    return token_info["access_token"]


async def ensure_has_oauth_token(oauth: OAuth2Session):
    async def first_time_auth():
        from app.config.podbean import client_id, client_secret
        from app.config.server import host, port

        [client_id, client_secret, host, port] = await asyncio.gather(
            client_id(), client_secret(), host(), port()
        )

        def sync():
            authorization_url, _ = oauth.authorization_url(oauth_url)

            logging.critical(f"Please visit the link below:\n{authorization_url}")
            code = get_oauth_code(host, port)
            return oauth.fetch_token(
                token_url=token_url,
                code=code,
                auth=(client_id, client_secret),
                client_id=client_id,
                client_secret=client_secret,
            )

        return await run_sync(sync)

    from app.config.pickle import access_code_pickle_path

    await load_pickle(await access_code_pickle_path(), get_default=first_time_auth)


async def add_to_podbean(
    oauth: OAuth2Session, video: YtdlPafy, audio_path: str, thumbnail_path: str
):
    """Uploads and publishes a video to Podbean
    """
    logging.debug(f"Getting PodBean access token...")
    access_token = await get_access_token(oauth)
    logging.debug(f"PodBean access token is '{access_token}'.")

    logging.debug(f"Uploading '{video.title}' to PodBean...")
    audio_file_key, thumbnail_file_key = await upload_episode_files(
        access_token, audio_path, thumbnail_path, video.title
    )
    await publish_episode(
        access_token, video.title, video.description, audio_file_key, thumbnail_file_key
    )
    logging.info(f"Successfully uploaded '{video.title}' to PodBean...")


async def main():
    from app.config.podbean import client_id, podbean_enabled

    [client_id, redirect] = await asyncio.gather(client_id(), redirect_uri())
    oauth = OAuth2Session(client_id=client_id, redirect_uri=redirect, scope=scope)
    await ensure_has_oauth_token(oauth)

    await asyncio.sleep(5)  # sleep 5s to wait for rabbitmq server to go up

    async for video in get_videos(topic="new_video/podbean"):
        [enabled, valid_title] = await asyncio.gather(
            podbean_enabled(), is_valid_title(video.title)
        )

        if not enabled:
            logging.debug(
                f"PodBean processing not enabled. Skipping video '{video.title}'."
            )
            continue

        if not valid_title:
            logging.debug(
                f"Video '{video.title}' skipped because the title was not compatible with the configuration patterns."
            )
            continue

        logging.debug(f"Download audio and thumbnail for '{video.title}'")
        [audio_path, thumbnail_path] = await asyncio.gather(
            download_audio(video), download_thumbnail(video)
        )

        logging.debug(f"Adding video '{video.title}' to PodBean")
        await add_to_podbean(oauth, video, audio_path, thumbnail_path)


if __name__ == "__main__":
    setup_logging("app.services.podbean")
    asyncio.run(log_exceptions(main, logging))
