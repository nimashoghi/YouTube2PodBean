def is_valid_title(title):
    import re
    from app.config import title_pattern, title_negative_pattern

    return re.search(title_pattern(), title, re.IGNORECASE) is not None and (
        not title_negative_pattern()
        or re.search(title_negative_pattern(), title, re.IGNORECASE) is None
    )


def sanitize_title(title):
    return "".join(
        [c for c in title if c.isalpha() or c.isdigit() or c == " "]
    ).rstrip()


def download_thumbnail(video):
    from app.download import download_to_path

    title = sanitize_title(video.title)
    url = video.bigthumbhd if video.bigthumbhd else video.bigthumb

    def get_url_extension(url, default="jpg"):
        import re

        match = re.search(url, r"\.(.+)\s*$")
        return match[1] if match else default

    print(f"Downloading thumbnail of '{title}' from {url}")

    return download_to_path(url, f"/tmp/{title}.{get_url_extension(url)}")


def download_youtube_audio(video):
    from app.download import download_to_path

    best = video.getbestaudio(preftype="m4a")

    title = sanitize_title(video.title)
    url = best.url

    print(f"Downloading audio stream of '{title}' from {url}")

    return download_to_path(url, f"/tmp/{title}.{best.extension}")


def is_processed(video):
    from app.config import processed_pickle_path, load_pickle, save_pickle

    id = video.videoid
    processed = load_pickle(processed_pickle_path(), get_default=lambda: set([]))
    if id in processed:
        return True
    else:
        print(f"Added {id} to processed")

        save_pickle(processed_pickle_path(), set([id, *processed]))
        return False


def process_new_video(callback, new=False):
    def process(video):
        if is_processed(video):
            return False

        mp3_path = download_youtube_audio(video)
        thumbnail_path = download_thumbnail(video)
        callback(video, video.title, video.description, mp3_path, thumbnail_path, new)

        return True

    return process


def get_uploads_playlist_id():
    from app.config import channel_id

    playlist_id = channel_id()
    if playlist_id[1] == "C":
        return f"{playlist_id[:1]}U{playlist_id[2:]}"
    else:
        return playlist_id


def get_all_uploads(refetch_latest=0):
    import pafy
    from itertools import islice
    from app.config import load_pickle, save_pickle, playlist_history_pickle_path

    new_playlist = pafy.get_playlist2(get_uploads_playlist_id())
    saved_playlist = load_pickle(
        playlist_history_pickle_path(), lambda new_playlist=new_playlist: new_playlist
    )
    old_count = len(saved_playlist) - refetch_latest
    count_difference = max([len(new_playlist) - old_count, 0])

    new_items_in_playlist = [*islice(new_playlist, 0, count_difference)]
    saved_playlist = [
        *new_items_in_playlist,
        *islice(saved_playlist, refetch_latest, len(saved_playlist)),
    ]
    save_pickle(playlist_history_pickle_path(), saved_playlist)

    return new_items_in_playlist, saved_playlist


def check_start_from(videos, start_from):
    if not start_from:
        yield from videos
    else:
        for item in videos:
            yield item
            if item.videoid == start_from:
                print(
                    f'Video start point detected. Checking videos up to "{item.title}"'
                )
                break


def detect_videos(f, new_only=True, start_from=None):
    from app.config import youtube_enabled

    if not youtube_enabled():
        print("YouTube polling not enabled. Skipping current loop")
        return

    from app.config import video_process_delay
    from time import sleep

    if start_from:
        print(f'Video start point detected. Checking videos up to "{start_from}"')

    new_items, all_videos = get_all_uploads()
    items = reversed(
        [
            item
            for item in check_start_from(
                all_videos if not new_only else new_items, start_from
            )
            if is_valid_title(item.title)
        ]
    )

    for item in items:
        if not f(item):
            continue

        delay = video_process_delay()
        print(f"Finished processing {item.title}. Waiting for {delay} seconds")
        sleep(delay)
