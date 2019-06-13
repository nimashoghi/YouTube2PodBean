import asyncio
from typing import Callable


async def run_sync(func: Callable):
    return await asyncio.get_event_loop().run_in_executor(executor=None, func=func)
