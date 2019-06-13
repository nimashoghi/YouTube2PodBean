from app.util import create_config

youtube_enabled = create_config("YouTube:Enabled", default=True)
youtube_api_key = create_config("YouTube:ApiKey", default="")
start_from = create_config("YouTube:StartFrom", default="")
video_process_delay = create_config("YouTube:VideoProcessDelay", default=10.0)
channel_id = create_config("YouTube:ChannelId")
polling_rate = create_config("YouTube:PollingRate", default=60.0)
manual_videos = create_config("YouTube:CustomVideos", default=[])
youtube_num_iterations_until_refetch = create_config(
    "YouTube:NumIterationsUntilRefetch", default=10
)
youtube_default_avatar = create_config(
    "YouTube:DefaultAvatarUrl", default="https://i.imgur.com/eYw9nVR.jpg"
)
