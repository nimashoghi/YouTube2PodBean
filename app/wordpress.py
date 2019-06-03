from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts


def make_client():
    from app.config import wp_password, wp_username, wp_xmlrpc_url

    if not wp_username() or not wp_password() or not wp_xmlrpc_url():
        return None

    return Client(wp_xmlrpc_url(), wp_username(), wp_password())


def make_embed_code(video):
    from app.config import wp_embed_width, wp_embed_height

    return f"""<iframe width="{wp_embed_width()}" height="{wp_embed_height()}" src="https://www.youtube.com/embed/{video.videoid}" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""


def add_anchor_to_urls(text: str):
    import re

    from app.constants import URL_REGEX

    return re.sub(URL_REGEX, r'<a href="\1">\1</a>', text)


def process_description(description):
    return add_anchor_to_urls(description)


def post_video(video):
    from app.config import wp_enabled

    if not wp_enabled():
        print(
            f'WordPress posting not enabled. Skipping sending "{video.title}" to WordPress.'
        )
        return None

    client = make_client()

    post = WordPressPost()
    post.title = video.title
    post.content = (
        f"{make_embed_code(video)}<hr />{process_description(video.description)}"
    )
    post.post_status = "publish"

    id = client.call(posts.NewPost(post))
    print(f'Successfully created WordPress post (ID = {id}) for "{video.title}"')