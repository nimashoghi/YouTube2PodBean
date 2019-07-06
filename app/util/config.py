import json
import os
from functools import reduce
from typing import Any, Union

import aiofiles


class Config:
    def __init__(self, config_name: str, default: Any = None):
        [*self.config_path, self.config_name] = config_name.split(":")
        self.default = default

    def _get_value_sync(self, data: dict) -> Any:
        try:
            value = reduce(
                lambda acc, update: acc[update],
                [*self.config_path, self.config_name],
                data,
            )
        except BaseException:
            if self.default is None:
                raise
            elif callable(self.default):
                value = self.default()
            else:
                value = self.default
        return value

    def _set_value_sync(self, data: dict, value: Any, settings_file: str) -> Any:
        config = data
        for path in self.config_path:
            if path not in config:
                config[path] = {}
            config = config[path]
        config[self.config_name] = value

        with open(settings_file, mode="w") as f:
            f.write(json.dumps(data, indent=4))

        return value

    def _retrieve_sync(self, value: Union[Any, None] = None) -> Any:
        settings_file = os.environ.get("SETTINGS_FILE", "./settings.json")

        data: dict
        if not os.path.exists(settings_file):
            data = {}
            with open(settings_file, mode="w") as f:
                f.write(json.dumps(data, indent=4))
        else:
            with open(settings_file, mode="r") as f:
                data = json.loads(f.read())

        if value is None:
            return self._get_value_sync(data)
        else:
            return self._set_value_sync(data, value, settings_file)

    def sync(self, value: Union[Any, None] = None) -> Any:
        return self._retrieve_sync(value=value)

    async def _get_value(self, data: dict) -> Any:
        try:
            value = reduce(
                lambda acc, update: acc[update],
                [*self.config_path, self.config_name],
                data,
            )
        except BaseException:
            if self.default is None:
                raise
            elif callable(self.default):
                value = await self.default()
            else:
                value = self.default
        return value

    async def _set_value(self, data: dict, value: Any, settings_file: str) -> Any:
        config = data
        for path in self.config_path:
            if path not in config:
                config[path] = {}
            config = config[path]
        config[self.config_name] = value

        async with aiofiles.open(settings_file, mode="w") as f:
            await f.write(json.dumps(data, indent=4))

        return value

    async def _retrieve(self, value: Union[Any, None] = None) -> Any:
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
            return await self._get_value(data)
        else:
            return await self._set_value(data, value, settings_file)

    async def __call__(self, value: Union[Any, None] = None) -> Any:
        return await self._retrieve(value=value)


def create_config(config_name: str, default: Any = None):
    return Config(config_name=config_name, default=default)
