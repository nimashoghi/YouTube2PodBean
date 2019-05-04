from typing import Callable

from requests_oauthlib import OAuth2Session

from server import get_oauth_code, host, port

client_id = "f0c1685729f99b7e953f2"
client_secret = "68eadbf5496e28d60f010"
redirect_uri = f"http://{host}:{port}"
scope = ["podcast_read", "podcast_update", "episode_read", "episode_publish"]

oauth_url = "https://api.podbean.com/v1/dialog/oauth"
token_url = "https://api.podbean.com/v1/oauth/token"


def authorize(oauth: OAuth2Session):
    authorization_url, _ = oauth.authorization_url(oauth_url)
    print(f"Please visit the link below:\n{authorization_url}")
    return get_oauth_code()


def get_token(code: str, oauth: OAuth2Session):
    return oauth.fetch_token(
        token_url=token_url, code=code, client_id=client_id, client_secret=client_secret
    )


oauth = OAuth2Session(client_id=client_id, redirect_uri=redirect_uri, scope=scope)
code = authorize(oauth)
token_result = get_token(code, oauth)
access_token = token_result["access_token"]
