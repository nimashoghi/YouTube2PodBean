youtube_watch_url = "https://www.youtube.com/watch?v="
youtube_search_url = "https://www.googleapis.com/youtube/v3/search"


def make_youtube_link(id):
    return f"{youtube_watch_url}{id}"


def get_tokens():
    import pickle
    from datetime import datetime, timezone, timedelta
    from app.config import published_after_pickle_path, get_pickle

    published_after = get_pickle(
        published_after_pickle_path(),
        (datetime.now(timezone.utc) - timedelta(days=30)).astimezone(),
    )

    pickle.dump(
        datetime.now(timezone.utc).astimezone(),
        open(published_after_pickle_path(), "wb"),
    )

    return published_after.isoformat()


def build_params(**kwargs):
    from app.config import youtube_api_key, channel_id

    return dict(
        type="video",
        part="snippet",
        maxResults=50,
        channelId=channel_id(),
        order="date",
        key=youtube_api_key(),
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
    from app.config import title_pattern

    return False if re.search(title_pattern(), title, re.IGNORECASE) is None else True


from pafy import g


class ydl:
    def urlopen(self, url):
        return g.opener.open(url)

    def to_screen(self, *args, **kwargs):
        pass

    def to_console_title(self, *args, **kwargs):
        pass

    def trouble(self, *args, **kwargs):
        pass

    def report_warning(self, *args, **kwargs):
        pass

    def report_error(self, *args, **kwargs):
        pass


def download_to_path(url, path):
    import os, youtube_dl

    downloader = youtube_dl.downloader.http.HttpFD(
        ydl(), {"http_chunk_size": 10_485_760}
    )

    downloader.download(path, dict(url=url))
    print()

    return path


def download_thumbnail(video):
    import requests

    title = video.title
    url = video.bigthumb

    def get_url_extension(url, default="jpg"):
        import re

        match = re.search(url, r"\.(.+)\s*$")
        return match[1] if match else default

    print(f"Downloading thumbnail of '{title}' from {url}")

    return download_to_path(url, f"/tmp/{title}.{get_url_extension(url)}")


def download_youtube_audio(video):
    import requests

    best = video.getbestaudio(preftype="m4a")

    title = video.title
    url = best.url

    print(f"Downloading audio stream of '{title}' from {url}")
    return download_to_path(url, f"/tmp/{title}.{best.extension}")


def process_new_video(callback):
    def process(id):
        import pafy
        from app.config import youtube_api_key

        pafy.set_api_key(youtube_api_key())

        video = pafy.new(id)

        mp3_path = download_youtube_audio(video)
        thumbnail_path = download_thumbnail(video)
        callback(video.title, video.description, mp3_path, thumbnail_path)

    return process


def has_been_processed(id):
    import pickle
    from app.config import processed_videos_pickle_path, get_pickle, save_pickle

    processed_videos = get_pickle(processed_videos_pickle_path(), lambda: set([]))
    return id in processed_videos


def add_video_to_processed(id):
    import pickle
    from app.config import processed_videos_pickle_path, get_pickle, save_pickle

    processed_videos = get_pickle(processed_videos_pickle_path(), lambda: set([]))
    processed_videos.add(id)
    save_pickle(processed_videos_pickle_path(), processed_videos)


def iterate_items(f, items):
    for id, title in items:
        if not filter_by_title(title) or has_been_processed(id):
            continue
        add_video_to_processed(id)
        f(id)


def detect_new_videos(f):
    import json

    def get_video_title(id):
        import pafy

        return pafy.new(id).title

    from app.config import videos

    iterate_items(f, [(id, get_video_title(id)) for id in videos()])

    def get_items(json_data):
        return [
            (item["id"]["videoId"], item["snippet"]["title"])
            for item in json_data["items"]
        ]

    published_after = get_tokens()

    json_data = get_videos(published_after)
    next_page_token = json_data.get("nextPageToken")
    iterate_items(f, get_items(json_data))

    while next_page_token:
        json_data = get_videos(published_after, next_page_token)
        next_page_token = json_data.get("nextPageToken")
        iterate_items(f, get_items(json_data))


def get_all_uplaods():
    def get_uploads_playlist_id():
        from app.config import channel_id

        playlist_id = channel_id()
        return f"{playlist_id[:1]}U{playlist_id[2:]}"

    import pafy
    from itertools import islice
    from app.config import get_pickle, save_pickle, videos_pickle_path

    playlist_id = get_uploads_playlist_id()
    new_playlist = pafy.get_playlist2(
        f"https://www.youtube.com/playlist?list={playlist_id}"
    )
    saved_playlist = get_pickle(
        videos_pickle_path(), lambda new_playlist=new_playlist: new_playlist
    )
    old_count = len(saved_playlist)
    count_difference = max([len(new_playlist) - old_count, 0])

    new_items = [*islice(new_playlist, 0, count_difference), *saved_playlist]
    saved_playlist._items = new_items
    saved_playlist._len = len(new_items)
    save_pickle(videos_pickle_path(), saved_playlist)

    print(f"old_count: {old_count}; count_difference: {count_difference}")

    return new_items


if __name__ == "__main__":
    import json, pickle

    x = get_all_uplaods()
    print(vars(x[0]))
    # pickle.dump(), open("uploads.pickle", "wb"))
    print()


# import pickle

# uploads = pickle.load(open("uploads.pickle", "rb"))
# [vars(upload) for upload in uploads]
# vars(uploads[0]).keys()
# uploads[0].bigthumb
