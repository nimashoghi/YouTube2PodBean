def color_tuple_to_int(tuple):
    r, g, b = tuple
    return (
        ((r & 0xFF) << (0x2 * 0x8))
        | ((b & 0xFF) << (0x1 * 0x8))
        | ((g & 0xFF) << (0x0 * 0x8))
    )


def get_avatar(channel_id):
    from requests import get
    from pafy import g

    result = get(
        f"https://www.googleapis.com/youtube/v3/channels?part=snippet&fields=items%2Fsnippet%2Fthumbnails%2Fdefault&id={channel_id}&key={g.api_key}"
    ).json()

    return result["items"][0]["snippet"]["thumbnails"]["default"]["url"]


def send_webhook(video, jpg, avatar_url, webhook_url):
    from dateutil import parser
    from discord_webhook import DiscordEmbed, DiscordWebhook
    from datetime import datetime
    from colorthief import ColorThief

    webhook = DiscordWebhook(url=webhook_url)

    embed = DiscordEmbed()
    embed.set_color(color_tuple_to_int(ColorThief(jpg).get_color(quality=1)))
    embed.set_title(video.title)
    embed.set_description(video.watchv_url)
    embed.set_author(
        name=video.author,
        url=f"https://www.youtube.com/user/{video.username}",
        icon_url=get_avatar(video.username),
    )
    embed.set_timestamp(str(parser.parse(video.published)))
    embed.set_image(url=video.bigthumbhd, width=480, height=360)
    embed.set_footer(text=f"Duration: {video.duration}")

    webhook.add_embed(embed)
    webhook.execute()


def process_webhooks(video, jpg):
    from app.config import channel_id, webhook_url_list
    from dateutil import parser
    from discord_webhook import DiscordEmbed, DiscordWebhook

    avatar_url = get_avatar(channel_id())

    for webhook_url in webhook_url_list():
        send_webhook(video, jpg, avatar_url, webhook_url)
