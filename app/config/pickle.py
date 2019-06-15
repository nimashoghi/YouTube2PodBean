from app.util import create_config

access_code_pickle_path = create_config(
    "Pickle:AccessCode", default="pickles/access_code.pickle"
)
processed_pickle_path = create_config(
    "Pickle:Processed", default="pickles/processed.pickle"
)
playlist_history_pickle_path = create_config(
    "Pickle:PlaylistHistory", default="pickles/playlist_history.pickle"
)
podbean_posted_pickle_path = create_config(
    "Pickle:PodBeanPosted", default="pickles/podbean_posted.pickle"
)
webhook_posted_pickle_path = create_config(
    "Pickle:WebHookPosted", default="pickles/webhook_posted.pickle"
)
wp_post_history_pickle_path = create_config(
    "Pickle:WordPressPosted", default="pickles/wp_post_history.pickle"
)
