import re
from logging import getLogger

import wordpress_xmlrpc as xmlrpc

from app.util import URL_REGEX

logging = getLogger(__name__)


def make_client():
    from app.config import wp_password, wp_username, wp_xmlrpc_url

    username = wp_username()
    password = wp_password()
    xmlrpc_url = wp_xmlrpc_url()

    if not username or not password or not xmlrpc_url:
        logging.critical(
            f"Incomplete or invalid WP XMLRPC information set (username = '{username}'; password = '****'; XMLRPC url = '{xmlrpc_url}'). Skipping uploading to WordPress."
        )
        return None
    else:
        logging.debug(
            f"Creating WordPress client (username = '{username}'; password = '****'; XMLRPC url = '{xmlrpc_url}')..."
        )

    return xmlrpc.Client(xmlrpc_url, username, password)


def make_embed_code(video):
    from app.config import wp_embed_width, wp_embed_height

    return f"""<iframe width="{wp_embed_width()}" height="{wp_embed_height()}" src="https://www.youtube.com/embed/{video.videoid}" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""


def add_anchor_to_urls(text: str):
    return re.sub(URL_REGEX, r'<a href="\1">\1</a>', text)


def process_description(description):
    return add_anchor_to_urls(description)


def post_video(video):
    from app.config import wp_enabled

    if not wp_enabled():
        logging.info(
            f'WordPress posting not enabled. Skipping sending "{video.title}" to WordPress.'
        )
        return None

    client = make_client()
    if client is None:
        logging.critical(
            f"Failed to create XMLRPC client. Aborting posting video '{video.title}' to WordPress."
        )
        return None

    post = xmlrpc.WordPressPost()
    post.title = video.title
    post.content = (
        f"{make_embed_code(video)}<hr />{process_description(video.description)}"
    )
    post.post_status = "publish"

    id = client.call(xmlrpc.methods.posts.NewPost(post))
    logging.info(
        f"Successfully created WordPress post with '{id}' for video '{video.title}'"
    )
    return id
