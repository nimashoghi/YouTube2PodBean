async def video_found(video, title, description, mp3, jpg, *, new, oauth):
    from app.discord import post_to_discord
    from app.wordpress import post_to_wordpress
    from app.podbean import post_to_podbean

    if new:
        post_to_discord(video, jpg)
        post_to_wordpress(video)

    post_to_podbean(title, description, mp3, jpg, oauth)


async def main():
    from app.config import enabled
    from time import sleep

    while not enabled():
        print(
            "Application is not enabled (kill switch)... Checking again in 5 seconds."
        )
        sleep(5.0)

    from app.podbean import (
        get_access_token,
        get_oauth,
        refresh_access_token,
        upload_and_publish_episode,
    )

    oauth = get_oauth()

    process_video_callback = process_new_video(video_found, new=False)
    process_new_video_callback = process_new_video(video_found, new=True)

    print("Processing all videos...")
    detect_videos(process_video_callback, new_only=False, start_from=start_from())

    while True:
        print("------------------------")
        print()

        print("Processing manual videos...")
        for id in videos():
            process_video_callback(pafy.new(id))

        print("Processing new videos...")
        detect_videos(process_new_video_callback, start_from=start_from())

        print()
        print("------------------------")
        sleep(polling_rate())


if __name__ == "__main__":
    import logging
    from asyncio import run
    from multiprocessing import freeze_support

    logging.basicConfig(level=logging.INFO)

    freeze_support()

    run(main())
