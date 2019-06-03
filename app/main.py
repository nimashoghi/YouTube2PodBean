import mimetypes
import os.path
from typing import Callable

import requests
from requests_oauthlib import OAuth2Session

from app.config import client_id, client_secret, port, public_host
from app.server import get_oauth_code as get_oauth_code_from_server

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


def publish_episode(
    access_token: str,
    title: str,
    description: str,
    file_key: str,
    thumbnail_file_key: str,
    status="publish",
    type="public",
):
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


def upload_and_publish_episode(
    access_token: str, title: str, description: str, file_path: str, thumbnail_path: str
):
    from app.config import podbean_enabled

    if not podbean_enabled():
        return

    presigned_url, file_key = authorize_upload(access_token, file_path)
    upload_file(file_path, presigned_url)

    presigned_url, thumbnail_file_key = authorize_upload(access_token, thumbnail_path)
    upload_file(thumbnail_path, presigned_url)

    return publish_episode(
        access_token, title, description, file_key, thumbnail_file_key
    )


def refresh_access_token(oauth: OAuth2Session):
    from app.config import access_code_pickle_path, load_pickle, save_pickle

    token_info = load_pickle(access_code_pickle_path())
    new_token_info = oauth.refresh_token(
        token_url=token_url, refresh_token=token_info["refresh_token"]
    )
    token_info.update(new_token_info)
    save_pickle(access_code_pickle_path(), token_info)


def get_access_token(oauth: OAuth2Session):
    from app.config import access_code_pickle_path, load_pickle

    return load_pickle(access_code_pickle_path())["access_token"]


def ensure_has_oauth_token(oauth: OAuth2Session):
    from app.config import access_code_pickle_path, load_pickle

    def first_time_auth():
        authorization_url, _ = oauth.authorization_url(oauth_url)
        print(f"Please visit the link below:\n{authorization_url}")
        code = get_oauth_code_from_server()
        return oauth.fetch_token(
            token_url=token_url,
            code=code,
            client_id=client_id(),
            client_secret=client_secret(),
        )

    load_pickle(access_code_pickle_path(), get_default=first_time_auth)


def main():
    from app.config import enabled
    from time import sleep

    while not enabled():
        print(
            "Application is not enabled (kill switch)... Checking again in 5 seconds."
        )
        sleep(5.0)

    oauth = OAuth2Session(client_id=client_id(), redirect_uri=redirect_uri, scope=scope)
    ensure_has_oauth_token(oauth)

    import pafy
    from os import remove
    from app.detect import detect_videos, process_new_video
    from app.config import polling_rate, start_from, videos
    from app.webhooks import process_webhooks
    from app.wordpress import post_video

    def video_found(video, title, description, mp3, jpg, new):
        from oauthlib.oauth2.rfc6749.errors import (
            InvalidGrantError,
            TokenExpiredError,
            InvalidTokenError,
        )

        if new:
            process_webhooks(video, jpg)
            post_video(video)

        while True:
            try:
                access_token = get_access_token(oauth)

                print(f"\nUploading {title}")
                upload_and_publish_episode(
                    access_token, title, description, file_path=mp3, thumbnail_path=jpg
                )
                remove(mp3)
                remove(jpg)
                print(f"Uploaded {title}")
                break
            except (InvalidGrantError, TokenExpiredError, InvalidTokenError):
                print("Token expired... refreshing")
                refresh_access_token(oauth)

    process_video_callback = process_new_video(video_found, new=False)
    process_new_video_callback = process_new_video(video_found, new=True)

    print("Processing all videos...")
    detect_videos(process_video_callback, new_only=False, start_from=start_from())

    while True:
        print("------------------------")
        print()

        print("Processing manual videos...")
        for id in videos():
            process_video_callback(pafy.new(id))

        print("Processing new videos...")
        detect_videos(process_new_video_callback, start_from=start_from())

        print()
        print("------------------------")
        sleep(polling_rate())


if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()

    main()
