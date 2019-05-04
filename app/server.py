from ctypes import c_char_p
from multiprocessing import Manager, Process
from time import sleep

from flask import Flask, request

host = "127.0.0.1"
port = "23808"

def disable_logging():
    import logging
    log = logging.getLogger('werkzeug')
    log.disabled = True

def get_oauth_code():
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

    manager = Manager()
    code = manager.Value(c_char_p, "")
    server = Process(target=run_app, args=(code,))
    server.start()

    while not code.value:
        sleep(0.5)

    server.terminate()
    server.join()

    return code.value
