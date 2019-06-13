from app.util import create_config, get_public_ip

host = create_config("Server:Host", default="0.0.0.0")
port = create_config("Server:Port", default="23808")
public_host = create_config("Server:PublicHost", default=get_public_ip)
