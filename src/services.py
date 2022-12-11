from time import time

MSG_SEND: str = "./src/__pycache__/.msg"
MSG_RECV: str = "./src/__pycache__/_copy.msg"


def time_ms() -> int:
    return int(time() * 1000)
