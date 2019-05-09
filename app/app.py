import mimetypes
import os.path
from typing import Callable

import requests
from requests_oauthlib import OAuth2Session

from server import get_oauth_code, host, port

client_id = "6640ad8c00ead54453601"
client_secret = "01e8f0bcfadd28fb35aeb"
redirect_uri = f"http://{host}:{port}"
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
    return get_oauth_code()


def get_access_token(code: str, oauth: OAuth2Session):
    return oauth.fetch_token(
        token_url=token_url, code=code, client_id=client_id, client_secret=client_secret
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
    return requests.put(
        presigned_url,
        headers={"Content-Type": get_content_type(file_path)},
        data=open(file_path, "rb"),
    )


def publish_episode(
    access_token: str,
    file_key: str,
    title: str,
    content="",
    status="publish",
    type="public",
):
    result = requests.post(
        publish_episode_url,
        data=build_params(
            access_token,
            title=title,
            content=content,
            status=status,
            type=type,
            media_key=file_key,
        ),
    ).json()

    return result["episode"]


def upload_new_media(access_token: str, file_path: str):
    presigned_url, file_key = authorize_upload(access_token, file_path)
    upload_file(file_path, presigned_url)
    return publish_episode(access_token, file_key, get_file_name(file_path))


def get_new_access_token():
    oauth = OAuth2Session(client_id=client_id, redirect_uri=redirect_uri, scope=scope)
    oauth._client.grant_type = "client_credentials"
    code = authorize(oauth)
    return get_access_token(code, oauth)

def main():
    access_token = "3755babd3002cfcbac020451d6456b85a1ad7424"
    print(f"Your access token is {access_token}")

    # print(
    #     authorize_upload(access_token, f"{os.path.dirname(__file__)}/bensound-summer.mp3")
    # )
    # print(
    #     upload_file(f"{os.path.dirname(__file__)}/bensound-summer.mp3", presigned_url).text
    # )
    # get_content_type(f"./app/bensound-summer.mp3")
    access_token = get_new_access_token()
    print(
        upload_new_media(
            access_token, file_path=f"{os.path.dirname(__file__)}/bensound-creativeminds.mp3"
        )
    )

if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()

    main()
