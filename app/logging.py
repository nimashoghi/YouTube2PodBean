import logging
from itertools import accumulate


class ContextAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        msg, kwargs = super(ContextAdapter, self).process(msg, kwargs)

        return (f"[{self.extra['context']}] {msg}", kwargs)


class LoggingContext:
    adapter: logging.LoggerAdapter
    logger: logging.Logger
    name: str

    def __init__(self, logger, name):
        self.logger = logger
        self.name = name

        self.adapter = ContextAdapter(self.logger, extra=dict(context=name))

    def __enter__(self):
        self.logger.debug(f"Entered context '{self.name}'")
        return self.adapter

    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.debug(f"Exited context '{self.name}'")


def context(logger, name):
    return LoggingContext(logger, name)


def create_logger(name: str):
    source_logger = logging.getLogger(name)

    def wrapper(func):
        from functools import wraps

        @wraps(func)
        def wrapped(*args, **kwargs):
            with context(
                kwargs.get("logger", source_logger), f"{name}.{func.__name__}"
            ) as logger:
                kwargs["logger"] = logger
                return func(*args, **kwargs)

        return wrapped

    return source_logger, wrapper
