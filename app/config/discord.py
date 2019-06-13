from app.util import create_config

webhook_enabled = create_config("WebHook:Enabled", default=True)
webhook_url_list = create_config("WebHook:UrlList", default=[])
webhook_text_max_length = create_config("WebHook:TextMaxLength", default=100)
webhook_max_duration = create_config("WebHook:MaxDuration", default=0)
