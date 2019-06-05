from typing import Union

from pafy.backend_youtube_dl import YtdlPafy
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts

from app.logging import create_logger
from app.sync import asyncify

logger, log = create_logger(__name__)


@log
def make_client(*, logger=logger) -> Client:
    from app.config import wp_password, wp_username, wp_xmlrpc_url
    from wordpress_xmlrpc import Client

    username = wp_username()
    password = wp_password()
    xmlrpc_url = wp_xmlrpc_url()

    logger.debug(
        f"Received request to connect to WP with username='{username}' password='{password}' xmlrpc_url='{xmlrpc_url}'"
    )

    if not username or not password or not xmlrpc_url:
        logger.warning(
            f"Invalid WP username, password, or xmlrpc_url. Aborting WP connection."
        )
        return None

    client = Client(xmlrpc_url, username, password)
    logger.debug("WP client successfully created")
    return client


def make_embed_code(video: YtdlPafy) -> str:
    from app.config import wp_embed_width, wp_embed_height

    return f"""<iframe width="{wp_embed_width()}" height="{wp_embed_height()}" src="https://www.youtube.com/embed/{video.videoid}" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""


def process_description(description: str) -> str:
    def add_anchor_to_urls(text: str):
        import re

        from app.constants import URL_REGEX

        return re.sub(URL_REGEX, r'<a href="\1">\1</a>', text)

    return add_anchor_to_urls(description)


@log
@asyncify
def post_msg(client: Client, title: str, content: str, *, logger=logger) -> str:
    logger.debug("Creating and publishing WP post...")
    post = WordPressPost()
    post.title = title
    post.content = content
    post.post_status = "publish"
    id = client.call(posts.NewPost(post))
    logger.info(f'Successfully created WordPress post (ID {id}) for "{title}"')
    return id


@log
async def post_to_wordpress(video: YtdlPafy, *, logger=logger) -> Union[str, None]:
    from app.config import wp_enabled

    if not wp_enabled():
        logger.info(
            f'WordPress posting not enabled. Skipping sending "{video.title}" to WordPress.'
        )
        return None

    client = make_client()

    return await post_msg(
        client,
        video.title,
        f"{make_embed_code(video)}<hr />{process_description(video.description)}",
    )
