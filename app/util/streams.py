import asyncio
import pickle
from contextlib import asynccontextmanager
from logging import getLogger
from typing import AsyncIterator, Callable, List

import aiomqtt
from pafy.backend_youtube_dl import YtdlPafy

logging = getLogger(__name__)


@asynccontextmanager
async def create_client(manage_loop=True):
    from app.config.core import message_broker

    message_broker = await message_broker()
    loop = asyncio.get_event_loop()
    client = aiomqtt.Client()

    try:
        logging.debug(f"Starting MQTT loop")
        client.loop_start()
        logging.debug(f"Started MQTT loop")

        logging.debug(f"Connecting to message broker at '{message_broker}'")

        # connect
        connected = asyncio.Event(loop=loop)

        def on_connect(client, userdata, flags, rc):
            connected.set()

        client.on_connect = on_connect

        await client.connect(message_broker)
        await connected.wait()

        logging.debug(f"Connected to message broker at '{message_broker}'")

        yield client
    except BaseException as e:
        print(f"got exception {e}")
    finally:
        # disconnect
        logging.debug(f"Disconnecting from message broker at '{message_broker}'")
        disconnected = asyncio.Event(loop=loop)

        def on_disconnect(client, userdata, rc):
            disconnected.set()

        client.on_disconnect = on_disconnect

        client.disconnect()
        await disconnected.wait()
        logging.debug(f"Disconnected from message broker at '{message_broker}'")

        if manage_loop:
            logging.debug(f"Stopping MQTT loop")
            await client.loop_stop()
            logging.debug(f"Stopped MQTT loop")


@asynccontextmanager
async def subscribe_to_topic(client: aiomqtt.Client, topic: str, callback: Callable):
    try:
        loop = asyncio.get_event_loop()

        logging.debug(f"Subscribing to the following MQTT topic: '{topic}'")
        subscribed = asyncio.Event(loop=loop)

        def on_subscribe(client, userdata, mid, granted_qos):
            subscribed.set()

        client.on_subscribe = on_subscribe

        client.subscribe((topic, 2))
        await subscribed.wait()

        lock = asyncio.Lock(loop=loop)

        def on_message(client, userdata, message):
            async def handler():
                async with lock:
                    await callback(client, userdata, message)

            loop.create_task(handler())

        client.on_message = on_message

        logging.debug(f"Subscribed to the following MQTT topic: '{topic}'")
        yield client
    finally:
        logging.debug(f"Unsubscribing to the following MQTT topic: '{topic}'")
        await client.unsubscribe(topic)  # do not need the QOS for unsub
        logging.debug(f"Unsubscribed to the following MQTT topic: '{topic}'")


def new_video_event_handler(topic: str, delay=5.0, init=None):
    def decorator(original_func):
        async def fn():
            kwargs = {}
            if init is not None:
                kwargs = await init()

            async def callback(client, userdata, message):
                video: YtdlPafy = pickle.loads(message.payload)
                await original_func(video, **kwargs)

            async with create_client(manage_loop=False) as client:
                async with subscribe_to_topic(client, topic, callback) as client:
                    await client.loop_forever()

        asyncio.run(fn())
        return original_func

    return decorator


async def send_video(client: aiomqtt.Client, video: YtdlPafy, topics: List[str]):
    video_bytes = pickle.dumps(video)
    logging.debug(f"Sending video '{video.title}' to the following topics: '{topics}'")
    await asyncio.gather(
        *(
            asyncio.ensure_future(
                client.publish(topic, video_bytes, qos=2).wait_for_publish()
            )
            for topic in topics
        )
    )
