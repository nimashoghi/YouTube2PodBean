from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods import posts


def make_client():
    from app.config import wp_password, wp_username, wp_xmlrpc_url

    if not wp_username or not wp_username or not wp_xmlrpc_url:
        return None

    return Client(wp_xmlrpc_url, wp_username, wp_password)


def make_embed_code(video):
    from app.config import wp_embed_width, wp_embed_height

    return f"""<iframe width="{wp_embed_width}" height="{wp_embed_height}" src="https://www.youtube.com/embed/{video.videoid}" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>"""


def post_video(video):
    client = make_client()

    post = WordPressPost()
    post.title = video.title
    post.content = f'{make_embed_code(video)}<br /><br />Video Description:<br /><!-- wp:code --><pre class="wp-block-code"><code>{video.description}</code></pre><!-- /wp:code -->'
    post.post_status = "publish"

    return client.call(posts.NewPost(post))
