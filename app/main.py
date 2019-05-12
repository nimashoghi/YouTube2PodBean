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

get_podcasts_url = "https://api.podbean.com/v1/podcasts"
get_episodes_url = "https://api.podbean.com/v1/episodes"
authorize_upload_url = "https://api.podbean.com/v1/files/uploadAuthorize"
publish_episode_url = "https://api.podbean.com/v1/episodes"


def authorize(oauth: OAuth2Session):
    authorization_url, _ = oauth.authorization_url(oauth_url)
    print(f"Please visit the link below:\n{authorization_url}")
    return get_oauth_code_from_server()


def get_access_token(code: str, oauth: OAuth2Session):
    return oauth.fetch_token(
        token_url=token_url,
        code=code,
        client_id=client_id(),
        client_secret=client_secret(),
    )["access_token"]


def build_params(access_token, **kwargs):
    return dict(access_token=access_token, **kwargs)


def get_podcasts(access_token: str):
    result = requests.get(get_podcasts_url, params=build_params(access_token)).json()
    return result["podcasts"]


def get_episodes(access_token: str, podcast_id: str):
    result = requests.get(
        get_episodes_url, params=build_params(access_token, podcast_id=podcast_id)
    ).json()
    return result["episodes"]


def get_file_name(path: str):
    return os.path.basename(path)


def get_file_size(path: str):
    return os.path.getsize(path)


def get_content_type(path: str):
    type, _ = mimetypes.guess_type(path)
    return type if type else "audio/mpeg"


def authorize_upload(access_token: str, file_path: str):
    result = requests.get(
        authorize_upload_url,
        params=build_params(
            access_token,
            filename=get_file_name(file_path),
            filesize=get_file_size(file_path),
            content_type=get_content_type(file_path),
        ),
    ).json()
    return result["presigned_url"], result["file_key"]


def upload_file(file_path: str, presigned_url: str):
    r = requests.put(
        presigned_url,
        headers={"Content-Type": get_content_type(file_path)},
        data=open(file_path, "rb"),
    )
    if not r.ok:
        raise Exception("Failed to upload")


def process_description(description: str):
    import re

    description.replace("\n", "<br />")

    # url_regex = r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})"

    # for match in re.findall(url_regex, description):
    #     description = description.replace(match, f"<a href='{match}'>{match}</a>")

    # 500 char limit
    return description[0:500]


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
        data=build_params(
            access_token,
            title=title,
            content=process_description(description),
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


def upload_new_media(
    access_token: str, title: str, description: str, file_path: str, thumbnail_path: str
):
    presigned_url, file_key = authorize_upload(access_token, file_path)
    upload_file(file_path, presigned_url)

    presigned_url, thumbnail_file_key = authorize_upload(access_token, thumbnail_path)
    upload_file(thumbnail_path, presigned_url)

    return publish_episode(
        access_token, title, description, file_key, thumbnail_file_key
    )


def get_new_access_code(oauth):
    oauth._client.grant_type = "client_credentials"
    return authorize(oauth)


def get_oauth_code(oauth):
    from app.config import access_code_pickle_path, get_pickle

    return get_pickle(
        access_code_pickle_path(), lambda oauth=oauth: get_new_access_code(oauth)
    )


def main():
    oauth = OAuth2Session(client_id=client_id(), redirect_uri=redirect_uri, scope=scope)
    code = get_oauth_code(oauth)

    from time import sleep
    from os import remove
    from app.detect import detect_new_videos, process_new_video

    def callback(title, description, mp3, jpg):
        print(f"\nUploading {title}")
        upload_new_media(
            get_access_token(code, oauth),
            title,
            description,
            file_path=mp3,
            thumbnail_path=jpg,
        )
        remove(mp3)
        remove(jpg)
        print(f"Uploaded {title}")

    while True:
        print(".", end="")
        detect_new_videos(process_new_video(callback))

        sleep(60.0)


if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()

    main()
