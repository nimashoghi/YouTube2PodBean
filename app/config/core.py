from app.util import create_config

message_broker = create_config("MessageBroker", default="mqtt://message_broker/")
