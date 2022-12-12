import hashlib
import colorlog
from time import time

MSG_SEND: str = "./src/__pycache__/.msg"
MSG_RECV: str = "./src/__pycache__/_copy.msg"


def time_ms() -> int:
    return int(time() * 1000)


def md5_file(file_path: str) -> str:
    BLOCKSIZE = 65536
    hasher = hashlib.md5()
    with open(file_path, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
        return hasher.hexdigest()


formatter: colorlog.ColoredFormatter = colorlog.ColoredFormatter(
    log_colors={
        'DEBUG':    'white',
        'INFO':     'cyan',
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'red,bg_green',
    },
    secondary_log_colors={
        'message': {
            'DEBUG':    'white',
            'INFO':     'cyan',
            'WARNING':  'yellow',
            'ERROR':    'black,bg_white',
            'CRITICAL': 'purple,bg_light_black',
        },

    },
    style='%',
)
handler = colorlog.StreamHandler()
handler.setFormatter(formatter)

colorlog.getLogger('').addHandler(handler)
global log
log = colorlog.getLogger(__name__)
log.setLevel('DEBUG')
log.info("Logger initialized")
"""_summary_escape_codes = {
    "reset": esc(0),
    "bold": esc(1),
    "thin": esc(2),
}

escape_codes_foreground = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "purple": 35,
    "cyan": 36,
    "white": 37,
    "light_black": 90,
    "light_red": 91,
    "light_green": 92,
    "light_yellow": 93,
    "light_blue": 94,
    "light_purple": 95,
    "light_cyan": 96,
    "light_white": 97,
}

escape_codes_background = {
    "black": 40,
    "red": 41,
    "green": 42,
    "yellow": 43,
    "blue": 44,
    "purple": 45,
    "cyan": 46,
    "white": 47,
    "light_black": 100,
    "light_red": 101,
    "light_green": 102,
    "light_yellow": 103,
    "light_blue": 104,
    "light_purple": 105,
    "light_cyan": 106,
    "light_white": 107,
    # Bold background colors don't exist,
    # but we used to provide these names.
    "bold_black": 100,
    "bold_red": 101,
    "bold_green": 102,
    "bold_yellow": 103,
    "bold_blue": 104,
    "bold_purple": 105,
    "bold_cyan": 106,
    "bold_white": 107,
}
    """
