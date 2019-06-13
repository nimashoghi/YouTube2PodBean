from app.util import create_config

wp_enabled = create_config("WordPress:Enabled", default=True)
wp_xmlrpc_url = create_config("WordPress:XmlRpcUrl", default="")
wp_username = create_config("WordPress:Username", default="")
wp_password = create_config("WordPress:Password", default="")
wp_embed_width = create_config("WordPress:EmbedWidth", default=560)
wp_embed_height = create_config("WordPress:EmbedHeight", default=315)
wp_max_duration = create_config("WordPress:MaxDuration", default=0)
