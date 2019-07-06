import asyncio

from app.util import create_config

logging_webhook_urls = create_config("Logging:WebHookUrlList", default=[])
