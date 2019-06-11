import time
from collections import OrderedDict
from itertools import chain, islice
from logging import getLogger
from typing import Set

import pafy
import pafy.g
import requests
import rx
import rx.operators
from pafy.backend_youtube_dl import YtdlPafy
from rx.core.typing import Observer

from app.data import VideoStreamObject
from app.download import download_audio, download_thumbnail
from app.util import load_pickle, sanitize_title, save_pickle

logging = getLogger(__name__)


def get_youtube_api_key() -> str:
    from app.config import youtube_api_key

    # TODO: check youtube api and get the API key that is available

    api_key = youtube_api_key()
    return api_key if api_key else pafy.g.api_key


def get_avatar(username_or_channel_id: str) -> str:
    try:
        # if a channel does not have a proper username, `username_or_channel_id` will include the channel id
        username = None
        channel_id = None
        channel_info: dict = {}

        # channel ids start w/ UC and have 24 chars
        if len(username_or_channel_id) == 24 and username_or_channel_id.startswith(
            "UC"
        ):
            channel_id = username_or_channel_id
            channel_info = dict(id=channel_id)
        else:
            username = username_or_channel_id
            channel_info = dict(forUsername=username)

        logging.debug(
            "Trying to get avatar for YouTube channel with "
            + f"channel id '{channel_id}'"
            if channel_id
            else f"username '{username}'"
        )
        response = requests.get(
            f"https://www.googleapis.com/youtube/v3/channels",
            params=dict(
                part="snippet",
                fields="items/snippet/thumbnails/default",
                key=get_youtube_api_key(),
                **channel_info,
            ),
        ).json()

        return response["items"][0]["snippet"]["thumbnails"]["default"]["url"]
    except:
        from app.config import webhook_default_avatar

        default_avatar = webhook_default_avatar()
        logging.critical(
            f"Could not get avatar. Using default avatar ({default_avatar}) instead."
        )
        return default_avatar


def get_all_uploads(refetch_latest=5):
    def get_playlist_id_for_channel_id(channel_id: str) -> str:
        # in YouTube, taking a channel ID and changing the second letter from "C" to "U" gives you a playlist with all that channel's uploads
        return (
            f"{channel_id[:1]}U{channel_id[2:]}" if channel_id[1] == "C" else channel_id
        )

    def video_to_ordered_pairs(videos):
        return reversed([(video.videoid, video) for video in videos])

    from app.config import channel_id, playlist_history_pickle_path

    playlist_id = get_playlist_id_for_channel_id(channel_id())

    # get_playlist2 lazy loads the basic video information first and then gets pafy objects for each on iteration
    # this means that we can load the list and only add the set of videos we need to prevent spamming YouTube
    new_playlist = pafy.get_playlist2(playlist_id)
    logging.debug(
        f"Getting all YouTube videos for the playlist '{new_playlist.title}'."
    )

    # videos are saved into the pickle file as an ordered dictionary in ascending chronological order (i.e. videos[0] will be the first video uploaded)
    saved_playlist = load_pickle(
        playlist_history_pickle_path(),
        lambda new_playlist=new_playlist: OrderedDict(
            video_to_ordered_pairs(new_playlist)
        ),
    )

    new_count = len(new_playlist)
    old_count = len(saved_playlist)
    logging.debug(
        f"Playlist '{new_playlist.title}' currently has {new_count} videos. Previously, it had {old_count} videos."
    )

    # if a video is removed, then the playlist's old_count will be more than the new_count
    if old_count > new_count:
        logging.debug(
            f"Deleted YouTube video detected for playlist '{new_playlist.title}'. Refetching the entire playlist!"
        )

        # a video was deleted, so we completely refetch the playlist
        saved_playlist = OrderedDict(video_to_ordered_pairs(new_playlist))
    elif old_count == new_count:
        # if the counts are equal, we expect the latest 5 videos to be exactly the same
        old_videos = saved_playlist.items()
        for i in range(0, refetch_latest):
            old = old_videos[-(i + 1)]  # new_playlist has index -1 == latest video
            new = new_playlist[i]  # new_playlist has index 0 == latest video

            if old.id != new.id:
                logging.info(
                    f"Deleted video detected. The video at position '{i}' (where position 0 is the latest video) in the playlist was expected to be video '{old.title}' but was '{new.title}'."
                )
                saved_playlist = OrderedDict(video_to_ordered_pairs(new_playlist))
                break
    else:
        logging.debug(
            f"No deleted videos detected for the current iteration of the playlist '{new_playlist.title}'."
        )
        # we didn't detect a deleted video, so we get the latest videos only
        saved_playlist = OrderedDict(
            chain(
                saved_playlist.items(),
                video_to_ordered_pairs(
                    islice(new_playlist, 0, new_count - old_count + refetch_latest)
                ),
            )
        )

    return save_pickle(playlist_history_pickle_path(), saved_playlist)


def get_videos_loop(observer: Observer[YtdlPafy]):
    from app.config import polling_rate, youtube_enabled

    def wait_until_next_iteration():
        wait_time = polling_rate()
        logging.debug(f"Sleeping for {wait_time} seconds until next iteration...")
        time.sleep(polling_rate())

    while True:
        if not youtube_enabled():
            logging.critical("YouTube polling not enabled. Skipping current iteration.")
            wait_until_next_iteration()
            continue

        for video in get_all_uploads():
            observer.on_next(video)

        wait_until_next_iteration()


def is_new_video(video: YtdlPafy) -> bool:
    from app.config import processed_pickle_path

    processed: Set[str] = load_pickle(
        processed_pickle_path(), get_default=lambda: set([])
    )
    return video.videoid in processed


def create_video_stream_object(video: YtdlPafy) -> VideoStreamObject:
    title = sanitize_title(video.title)
    return VideoStreamObject(
        id=video.videoid,
        video=video,
        audio=download_audio(video, title),
        thumbnail=download_thumbnail(video, title),
    )


def detect_new_videos():
    def log_new_video_detected(obj: VideoStreamObject):
        logging.debug(
            f"Processing video = '{obj.video}';\n title = '{obj.video.title}';\n description = '{obj.video.description}';\n audio_path = '{obj.audio}';\n thumbnail_path = '{obj.thumbnail}'"
        )

    return rx.create(get_videos_loop).pipe(
        rx.operators.filter(is_new_video),
        rx.operators.map(create_video_stream_object),
        rx.operators.do(log_new_video_detected),
    )
