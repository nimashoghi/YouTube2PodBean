import asyncio
from collections import OrderedDict
from itertools import chain, islice

import pafy
import pafy.g
from pafy.backend_youtube_dl import YtdlPafy

from app.util import (
    create_client,
    entrypoint,
    load_pickle,
    save_pickle,
    send_video,
    setup_logging,
)

logging = setup_logging("app.services.youtube")


upload_check_iteration: dict = {}


async def get_all_uploads(refetch_latest=5):
    def get_playlist_id_for_channel_id(channel_id: str) -> str:
        # in YouTube, taking a channel ID and changing the second letter from "C" to "U" gives you a playlist with all that channel's uploads
        return (
            f"{channel_id[:1]}U{channel_id[2:]}" if channel_id[1] == "C" else channel_id
        )

    def video_to_ordered_pairs(videos):
        return reversed([(video.videoid, video) for video in videos])

    def process_start_from(dict: OrderedDict, start_from: str):
        # dict is reversed
        if not start_from:
            index = 0
            logging.info(
                f"YouTube 'start from' setting not set. Checking the entire YouTube playlist."
            )
        elif start_from in dict:
            index = tuple(dict).index(start_from)
            logging.info(
                f"YouTube 'start from' is set to '{start_from}' and was found at index {index} (index 0 is the earliest video)."
            )
        else:
            raise Exception(f"Start from video '{start_from}' was not found!")

        items = list(dict.items())
        skipped, selected = items[:index], items[index:]
        logging.debug(f"Skip index set to '{index}'.")
        logging.debug(f"Skipping the following videos: {[id for id, _ in skipped]}.")
        logging.debug(f"Selecting the following videos: {[id for id, _ in selected]}.")
        for _, video in selected:
            yield video

    from app.config.youtube import (
        channel_id,
        start_from,
        youtube_num_iterations_until_refetch,
    )
    from app.config.pickle import playlist_history_pickle_path

    channel_id, pickle_path, num_iterations_until_refetch, start_from = await asyncio.gather(
        channel_id(),
        playlist_history_pickle_path(),
        youtube_num_iterations_until_refetch(),
        start_from(),
    )
    playlist_id = get_playlist_id_for_channel_id(channel_id)

    # get_playlist2 lazy loads the basic video information first and then gets pafy objects for each on iteration
    # this means that we can load the list and only add the set of videos we need to prevent spamming YouTube
    new_playlist = pafy.get_playlist2(playlist_id)
    logging.debug(
        f"Getting all YouTube videos for the playlist '{new_playlist.title}'."
    )

    # periodically refetch the entire playlist
    global upload_check_iteration
    iteration_count = upload_check_iteration.get(playlist_id, 0)
    logging.debug(
        f"Iteration count for playlist '{new_playlist.title}' is {iteration_count}"
    )
    if iteration_count % num_iterations_until_refetch == 0:
        logging.info(
            f"Refetching the YouTube playlist '{new_playlist.title}' due to iteration count."
        )
        upload_check_iteration[playlist_id] = iteration_count + 1
        for video in process_start_from(
            await save_pickle(
                pickle_path, OrderedDict(video_to_ordered_pairs(new_playlist))
            ),
            start_from,
        ):
            yield video

        return

    # videos are saved into the pickle file as an ordered dictionary in ascending chronological order (i.e. videos[0] will be the first video uploaded)
    old_playlist: OrderedDict = await load_pickle(
        pickle_path,
        lambda new_playlist=new_playlist: OrderedDict(
            video_to_ordered_pairs(new_playlist)
        ),
    )
    saved_playlist = old_playlist

    new_count = len(new_playlist)
    old_count = len(old_playlist)
    logging.debug(
        f"Playlist '{new_playlist.title}' currently has {new_count} videos. Previously, it had {old_count} videos."
    )

    # if a video is removed, then the playlist's old_count will be more than the new_count
    if old_count > new_count:
        logging.debug(
            f"old_count > new_count ===> Deleted YouTube video detected for playlist '{new_playlist.title}'. Refetching the entire playlist."
        )

        # a video was deleted, so we completely refetch the playlist
        saved_playlist = OrderedDict(video_to_ordered_pairs(new_playlist))
    elif old_count == new_count:
        logging.debug(f"old_count == new_count")
        # if the counts are equal, we expect the latest 5 videos to be exactly the same
        old_videos = list(old_playlist.items())
        for i in range(0, min(refetch_latest, old_count, new_count)):
            old_id, old = old_videos[
                -(i + 1)
            ]  # new_playlist has index -1 == latest video
            new = new_playlist[i]  # new_playlist has index 0 == latest video

            if old_id != new.videoid:
                logging.info(
                    f"Deleted video detected. The video at position '{i}' (where position 0 is the latest video) in the playlist was expected to be video '{old.title}' but was '{new.title}'. Refetching the entire playlist."
                )
                saved_playlist = OrderedDict(video_to_ordered_pairs(new_playlist))
                break
    else:
        logging.debug(
            f"old_count < new_count ===> No deleted videos detected for the current iteration of the playlist '{new_playlist.title}'."
        )
        # we didn't detect a deleted video, so we get the latest videos only
        saved_playlist = OrderedDict(
            chain(
                old_playlist.items(),
                video_to_ordered_pairs(
                    islice(new_playlist, 0, new_count - old_count + refetch_latest)
                ),
            )
        )

    upload_check_iteration[playlist_id] = iteration_count + 1
    for video in process_start_from(
        await save_pickle(pickle_path, saved_playlist), start_from
    ):
        yield video


async def is_new_video(video: YtdlPafy) -> bool:
    from app.config.pickle import processed_pickle_path

    processed = await load_pickle(
        await processed_pickle_path(), get_default=lambda: set([])
    )
    return video.videoid not in processed


async def mark_video_as_processed(video: YtdlPafy):
    from app.config.pickle import processed_pickle_path

    pickle_path = await processed_pickle_path()

    await save_pickle(
        pickle_path,
        set(
            [
                *await load_pickle(pickle_path, get_default=lambda: set([])),
                video.videoid,
            ]
        ),
    )


if __name__ == "__main__":

    async def main():
        from app.config.youtube import polling_rate, youtube_enabled

        await asyncio.sleep(5)  # sleep 5s to wait for rabbitmq server to go up

        async with create_client() as client:
            logging.debug(f"Waiting for all other services to connect...")
            await asyncio.sleep(5)

            while True:
                [enabled, wait_time] = await asyncio.gather(
                    youtube_enabled(), polling_rate()
                )

                if not enabled:
                    logging.info(
                        f"YouTube module is disabled. Skipping detection loop."
                    )
                    return

                logging.debug(
                    f"YouTube module is enabled. Running YouTube detection loop."
                )

                async for video in get_all_uploads():
                    logging.debug(f"Checking video '{video}' in uploads...")
                    if not await is_new_video(video):
                        logging.debug(
                            f"Ignoring video '{video.title}' because it is not new."
                        )
                        return

                    logging.info(f"New video '{video.title}' detected. Processing")

                    await send_video(
                        client,
                        video,
                        [
                            "new_video/discord",
                            "new_video/podbean",
                            "new_video/wordpress",
                        ],
                    )
                    await mark_video_as_processed(video)

                await asyncio.sleep(wait_time)

    entrypoint(main, logger=logging)
