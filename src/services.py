import logging
from time import time
import colorlog


def time_ms() -> int:
    return int(time() * 1000)


def fetchLogger(name="None"):
    log = logging.getLogger(__name__)
    if log.hasHandlers():
        # Logger is already configured, remove all handlers
        log.handlers = []
    # Configure the logger as before.
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s:%(name)s:%(message)s'))

    log = colorlog.getLogger('example')
    log.addHandler(handler)

    return log
