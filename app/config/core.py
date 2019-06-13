from app.util import create_config

message_broker = create_config(
    "MessageBroker", default="amqp://user:password@message_broker/"
)
