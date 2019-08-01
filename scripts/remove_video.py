#!/usr/bin/env python3

import os.path
import pickle
from argparse import ArgumentParser
from collections import OrderedDict
from typing import Any


def load(path: str):
    with open(path, "rb") as f:
        return pickle.load(f)


def save(path: str, obj: Any):
    with open(path, "wb") as f:
        return pickle.dump(obj, f)


def remove_video(
    video_id: str,
    *,
    videos_path: str,
    webhook_posted_path: str,
    podbean_posted_path: str,
    wp_post_history_path: str,
):
    # videos.pickles
    videos: OrderedDict = load(videos_path)
    if video_id in videos:
        videos.pop(video_id)
        save(videos_path, videos)
        print(f"Video '{video_id}' removed from pickle file '{videos_path}'.")
    else:
        print(f"Video '{video_id}' does not exist in pickle file '{videos_path}'.")

    # webhook_posted.pickle
    webhook_posted: set = load(webhook_posted_path)
    if video_id in webhook_posted:
        webhook_posted.remove(video_id)
        save(webhook_posted_path, webhook_posted)
        print(f"Video '{video_id}' removed from pickle file '{webhook_posted_path}'.")
    else:
        print(
            f"Video '{video_id}' does not exist in pickle file '{webhook_posted_path}'."
        )

    # podbean_posted.pickle
    podbean_posted: set = load(podbean_posted_path)
    if video_id in podbean_posted:
        podbean_posted.remove(video_id)
        save(podbean_posted_path, podbean_posted)
        print(f"Video '{video_id}' removed from pickle file '{podbean_posted_path}'.")
    else:
        print(
            f"Video '{video_id}' does not exist in pickle file '{podbean_posted_path}'."
        )

    # wp_post_history.pickle
    wp_post_history: set = load(wp_post_history_path)
    if video_id in wp_post_history:
        wp_post_history.remove(video_id)
        save(wp_post_history_path, wp_post_history)
        print(f"Video '{video_id}' removed from pickle file '{wp_post_history_path}'.")
    else:
        print(
            f"Video '{video_id}' does not exist in pickle file '{wp_post_history_path}'."
        )


def main():
    parser = ArgumentParser(
        description="Removes a set of videos from the processed list"
    )
    parser.add_argument(
        "--cwd",
        dest="cwd",
        default=".",
        help="Current working directory. All the path variables are processed relative to this CWD.",
    )
    parser.add_argument(
        "--videos-path",
        dest="videos_path",
        default="./pickles/videos.pickle",
        help="videos pickle path",
    )
    parser.add_argument(
        "--webhook-posted-path",
        dest="webhook_posted_path",
        default="./pickles/webhook_posted.pickle",
        help="webhook_posted pickle path",
    )
    parser.add_argument(
        "--podbean-posted-path",
        dest="podbean_posted_path",
        default="./pickles/podbean_posted.pickle",
        help="podbean_posted pickle path",
    )
    parser.add_argument(
        "--wp-post-history-path",
        dest="wp_post_history_path",
        default="./pickles/wp_post_history.pickle",
        help="wp_post_history pickle path",
    )
    parser.add_argument("video_id", nargs="+", help="List of video ids to process")

    args = parser.parse_args()
    for video_id in set(args.video_id):
        remove_video(
            video_id,
            videos_path=os.path.normpath(os.path.join(args.cwd, args.videos_path)),
            webhook_posted_path=os.path.normpath(
                os.path.join(args.cwd, args.webhook_posted_path)
            ),
            podbean_posted_path=os.path.normpath(
                os.path.join(args.cwd, args.podbean_posted_path)
            ),
            wp_post_history_path=os.path.normpath(
                os.path.join(args.cwd, args.wp_post_history_path)
            ),
        )


if __name__ == "__main__":
    main()
