from app.util import create_config

podbean_enabled = create_config("PodBean:Enabled", default=True)
client_id = create_config("PodBean:ClientId")
client_secret = create_config("PodBean:ClientSecret")
title_pattern = create_config("PodBean:TitlePattern", default=".+")
title_negative_pattern = create_config("PodBean:TitleNegativePattern", default="")
