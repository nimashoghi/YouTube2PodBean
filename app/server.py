from ctypes import c_char_p
from multiprocessing import Manager, Process, Value, set_start_method
from time import sleep
from typing import Any

from flask import Flask, request

from app.logging import create_logger
from app.sync import asyncify

set_start_method("spawn", True)

logger, log = create_logger(__name__)


@log
def run_app(expected_code: Value, *, logger=logger) -> None:
    from app.config import host, port

    app = Flask("OAuthServer")

    @app.route("/")
    def callback():  # pylint: disable=unused-variable
        request_code = request.args.get("code")

        if not request_code:
            return "Failed to authorize!"

        expected_code.value = request_code
        return "Successfully authorized!"

    app_host, app_port = host(), port()
    logger.info(f"Started OAuth server at {app_host}:{app_port}")
    app.run(host=app_host, port=app_port)


@asyncify
def get_oauth_code() -> None:
    manager = Manager()
    code: Any = manager.Value(c_char_p, "")

    server = Process(target=run_app, args=(code,))
    server.start()

    while not code.value:
        sleep(0.5)

    server.terminate()
    server.join()

    return code.value
