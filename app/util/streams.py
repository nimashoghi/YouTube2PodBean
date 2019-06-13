import asyncio
import pickle
from typing import AsyncIterator

import aio_pika as pika
from pafy.backend_youtube_dl import YtdlPafy


def encode_video(video: YtdlPafy):
    return pickle.dumps(video)


async def get_videos(
    connection: pika.Connection, exchange_name="videos_exchange"
) -> AsyncIterator[YtdlPafy]:
    channel: pika.Channel = await connection.channel()
    exchange = await channel.declare_exchange(
        exchange_name, type=pika.ExchangeType.FANOUT
    )
    queue: pika.Queue = await channel.declare_queue(durable=True, exclusive=True)
    await queue.bind(exchange)

    async with queue.iterator() as queue_iterator:
        async for message in queue_iterator:
            message: pika.IncomingMessage
            async with message.process():
                yield pickle.loads(message.body)


async def send_video(
    video: YtdlPafy, channel: pika.Channel, exchange_name="videos_exchange"
):
    exchange = await channel.declare_exchange(
        exchange_name, type=pika.ExchangeType.FANOUT
    )
    await exchange.publish(pika.Message(pickle.dumps(video)), routing_key="")
