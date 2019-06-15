import asyncio
import re
from datetime import datetime
from typing import Union

import dateutil.parser
import wordpress_xmlrpc as xmlrpc
from pafy.backend_youtube_dl import YtdlPafy

from app.util import (
    URL_REGEX,
    is_already_posted,
    load_pickle,
    mark_as_posted,
    new_video_event_handler,
    run_sync,
    save_pickle,
    setup_logging,
)

logging = setup_logging("app.services.wordpress")


async def make_client() -> xmlrpc.Client:
    from app.config.wordpress import wp_password, wp_username, wp_xmlrpc_url

    [username, password, xmlrpc_url] = await asyncio.gather(
        wp_username(), wp_password(), wp_xmlrpc_url()
    )

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


async def make_embed_code(video: YtdlPafy) -> str:
    from app.config.wordpress import wp_embed_width, wp_embed_height

    [wp_embed_width, wp_embed_height] = await asyncio.gather(
        wp_embed_width(), wp_embed_height()
    )

    # copied directly from the YouTube "share" window
    return f"""<iframe width="{wp_embed_width}" height="{wp_embed_height}" src="https://www.youtube.com/embed/{video.videoid}" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""


def add_anchor_to_urls(text: str) -> str:
    # adding anchor tags to each URL prevents WordPress from automatically embedding things into the post
    # for example, https://twitter.com/user will trigger WordPress to embed a list of tweets from the user
    # however, <a href="http://twitter.com/user">http://twitter.com/user</a> does not have this problem
    return re.sub(URL_REGEX, r'<a href="\1">\1</a>', text)


def process_description(description: str) -> str:
    return add_anchor_to_urls(description)


async def create_post_for_video(video: YtdlPafy) -> xmlrpc.methods.posts.NewPost:
    post = xmlrpc.WordPressPost()
    post.title = video.title
    post.content = (
        f"{await make_embed_code(video)}<hr />{process_description(video.description)}"
    )
    post.post_status = "publish"
    return xmlrpc.methods.posts.NewPost(post)


async def post_video(video: YtdlPafy) -> Union[str, None]:
    from app.config.wordpress import wp_enabled

    if not await wp_enabled():
        logging.info(
            f'WordPress posting not enabled. Skipping sending "{video.title}" to WordPress.'
        )
        return None

    client = await make_client()
    if client is None:
        logging.critical(
            f"Failed to create XMLRPC client. Aborting posting video '{video.title}' to WordPress."
        )
        return None

    post = await create_post_for_video(video)
    if not post:
        logging.critical(
            f"Failed to create WordPress post for video '{video.title}'. Aborting posting video '{video.title}' to WordPress"
        )
        return None

    id = await run_sync(lambda: client.call(post))
    logging.info(
        f"Successfully created WordPress post with '{id}' for video '{video.title}'"
    )
    return id


async def is_video_too_old(video: YtdlPafy):
    from app.config.wordpress import wp_max_duration

    max_duration = await wp_max_duration()
    return max_duration != 0 and (
        (datetime.now() - dateutil.parser.parse(video.published)).total_seconds()
        > max_duration
    )


if __name__ == "__main__":

    @new_video_event_handler("new_video/wordpress", logger=logging)
    async def on_new_video(video: YtdlPafy):
        from app.config.pickle import wp_post_history_pickle_path
        from app.config.wordpress import wp_enabled

        [enabled, too_old, already_posted] = await asyncio.gather(
            wp_enabled(),
            is_video_too_old(video),
            is_already_posted(video.videoid, wp_post_history_pickle_path),
        )

        if not enabled:
            logging.debug(
                f"WordPress publishing not enabled. Skipping video '{video.title}'."
            )
            return
        if already_posted:
            logging.info(
                f"Video '{video.title}' is already posted to WordPress. Skipping"
            )
            return
        if too_old:
            logging.info(
                f"Video '{video.title}' is too old to upload to WordPress. Skipping."
            )
            return

        logging.info(
            f"Video '{video.title}' has not been to WordPress. Posting the video to WordPRess"
        )

        await post_video(video)
        await mark_as_posted(video.videoid, wp_post_history_pickle_path)
