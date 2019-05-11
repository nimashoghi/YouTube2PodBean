youtube_watch_url = "https://www.youtube.com/watch?v="
youtube_search_url = "https://www.googleapis.com/youtube/v3/search"


def make_youtube_link(id):
    return f"{youtube_watch_url}{id}"


def get_tokens():
    import pickle
    from datetime import datetime, timezone, timedelta
    from config import published_after_pickle_path

    try:
        published_after = pickle.load(open(published_after_pickle_path, "rb"))
    except (OSError, IOError):
        published_after = (datetime.now(timezone.utc) - timedelta(days=30)).astimezone()

    pickle.dump(
        datetime.now(timezone.utc).astimezone(), open(published_after_pickle_path, "wb")
    )

    return published_after.isoformat()


def build_params(**kwargs):
    from config import youtube_api_key as key, channel_id

    return dict(
        type="video",
        part="snippet",
        maxResults=50,
        channelId=channel_id,
        order="date",
        key=key,
        **kwargs,
    )


def get_videos(published_after=None, page_token=None):
    import requests

    return requests.get(
        youtube_search_url,
        params=build_params(publishedAfter=published_after, pageToken=page_token),
    ).json()


def filter_by_title(title):
    import re
    from config import title_pattern

    return False if re.search(title_pattern, title, re.IGNORECASE) is None else True


def iterate_items(f, json_data):
    for item in json_data["items"]:
        id = item["id"]["videoId"]
        snippet = item["snippet"]
        title = snippet["title"]
        if not filter_by_title(title):
            continue
        thumbnail = snippet["thumbnails"]["high"]["url"]
        f(id, title, thumbnail, snippet)


def detect_new_videos(f):
    import json

    published_after = get_tokens()

    json_data = get_videos(published_after)
    next_page_token = json_data.get("nextPageToken")
    iterate_items(f, json_data)

    while next_page_token:
        json_data = get_videos(published_after, next_page_token)
        next_page_token = json_data.get("nextPageToken")
        iterate_items(f, json_data)


def download_thumbnail(title, url):
    import requests

    with open(f"{title}.jpg", "wb") as f:
        f.write(requests.get(url).content)


def process_new_video(callback):
    def process(id, title, thumbnail, snippet):
        from youtube_dl import YoutubeDL

        with YoutubeDL(
            params=dict(
                format="bestaudio/best",
                postprocessors=[
                    dict(
                        key="FFmpegExtractAudio",
                        preferredcodec="mp3",
                        preferredquality="192",
                    )
                ],
                outtmpl="%(title)s.%(ext)s",
            )
        ) as dl:
            dl.download([make_youtube_link(id)])
            download_thumbnail(title, thumbnail)
            callback(title, f"{title}.mp3", f"{title}.jpg")

    return process
