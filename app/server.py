from ctypes import c_char_p
from multiprocessing import Manager, Process, set_start_method
from time import sleep

from flask import Flask, request


def get_public_ip():
    from requests import get

    return get("https://api.ipify.org").text


host = "0.0.0.0"
public_host = get_public_ip()
port = "23808"

set_start_method("spawn", True)


def disable_logging():
    import logging

    log = logging.getLogger("werkzeug")
    log.disabled = True


def run_app(code):

    app = Flask("OAuthServer")
    disable_logging()

    @app.route("/")
    def callback():  # pylint: disable=unused-variable
        request_code = request.args.get("code")

        if not request_code:
            return "Failed to authorize!"

        code.value = request_code
        return "Successfully authorized!"

    app.run(host=host, port=port)


def get_oauth_code():

    manager = Manager()
    code = manager.Value(c_char_p, "")
    server = Process(target=run_app, args=(code,))
    server.start()

    while not code.value:
        sleep(0.5)

    server.terminate()
    server.join()

    return code.value
