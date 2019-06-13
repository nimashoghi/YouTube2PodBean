import json
import os
from functools import reduce
from typing import Any, Union

import aiofiles


def create_config(config_name: str, default: Any = None):
    [*config_path, config_name] = config_name.split(":")

    async def get_value(data: dict) -> Any:
        try:
            value = reduce(
                lambda acc, update: acc[update], [*config_path, config_name], data
            )
        except BaseException:
            if default is None:
                raise
            elif callable(default):
                value = await default()
            else:
                value = default
        return value

    async def set_value(data: dict, value: Any, settings_file: str) -> Any:
        config = data
        for path in config_path:
            if path not in config:
                config[path] = {}
            config = config[path]
        config[config_name] = value

        async with aiofiles.open(settings_file, mode="w") as f:
            await f.write(json.dumps(data, indent=4))

        return value

    async def retrieve(value: Union[Any, None] = None) -> Any:
        settings_file = os.environ.get("SETTINGS_FILE", "./settings.json")

        data: dict
        if not os.path.exists(settings_file):
            data = {}
            async with aiofiles.open(settings_file, mode="w") as f:
                await f.write(json.dumps(data, indent=4))
        else:
            async with aiofiles.open(settings_file, mode="r") as f:
                data = json.loads(await f.read())

        if value is None:
            return await get_value(data)
        else:
            return await set_value(data, value, settings_file)

    return retrieve
