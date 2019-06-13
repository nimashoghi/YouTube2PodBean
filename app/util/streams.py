import asyncio
import pickle
from contextlib import asynccontextmanager
from logging import getLogger
from typing import AsyncIterator, List

from hbmqtt.client import QOS_2, MQTTClient
from hbmqtt.mqtt.publish import PublishPacket, PublishPayload
from hbmqtt.session import ApplicationMessage
from pafy.backend_youtube_dl import YtdlPafy

logging = getLogger(__name__)


@asynccontextmanager
async def create_client():
    from app.config.core import message_broker

    message_broker = await message_broker()
    try:
        client = MQTTClient()
        logging.debug(f"Connecting to message broker at '{message_broker}'")
        await client.connect(message_broker)
        logging.debug(f"Connected to message broker at '{message_broker}'")
        yield client
    finally:
        logging.debug(f"Disconnecting from message broker at '{message_broker}'")
        await client.disconnect()
        logging.debug(f"Disconnected from message broker at '{message_broker}'")


@asynccontextmanager
async def subscribe_to_topic(client: MQTTClient, topic: str):
    try:
        logging.debug(f"Subscribing to the following MQTT topic: '{topic}'")
        await client.subscribe([(topic, QOS_2)])
        logging.debug(f"Subscribed to the following MQTT topic: '{topic}'")
        yield client
    finally:
        logging.debug(f"Unsubscribing to the following MQTT topic: '{topic}'")
        await client.unsubscribe([topic])  # do not need the QOS for unsub
        logging.debug(f"Unsubscribed to the following MQTT topic: '{topic}'")


async def get_videos(topic: str) -> AsyncIterator[YtdlPafy]:
    # TODO: Handle failure
    async with create_client() as client:
        async with subscribe_to_topic(client, topic):
            while True:
                message: ApplicationMessage = await client.deliver_message()
                logging.debug(
                    f"Received a new message from MQTT topic '{message.topic}'"
                )
                packet: PublishPacket = message.publish_packet
                if packet:
                    payload: PublishPayload = packet.payload
                    video = pickle.loads(payload.data)
                    yield video


async def send_video(client: MQTTClient, video: YtdlPafy, topics: List[str]):
    video_bytes = pickle.dumps(video)
    logging.debug(f"Sending video '{video.title}' to the following topics: '{topics}'")
    await asyncio.gather(
        *(
            asyncio.ensure_future(client.publish(topic, video_bytes, qos=QOS_2))
            for topic in topics
        )
    )
