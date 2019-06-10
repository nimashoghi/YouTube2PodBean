import multiprocessing as mp
import time
from ctypes import c_char_p

from flask import Flask, request

mp.set_start_method("spawn", True)


def run_app(code):
    from app.config import host, port

    app = Flask("OAuthServer")

    @app.route("/")
    def callback():  # pylint: disable=unused-variable
        request_code = request.args.get("code")

        if not request_code:
            return "Failed to authorize!"

        code.value = request_code
        return "Successfully authorized!"

    app.run(host=host(), port=port())


def get_oauth_code():
    manager = mp.Manager()
    code = manager.Value(c_char_p, "")
    server = mp.Process(target=run_app, args=(code,))
    server.start()

    while not code.value:
        time.sleep(0.5)

    server.terminate()
    server.join()

    return code.value
