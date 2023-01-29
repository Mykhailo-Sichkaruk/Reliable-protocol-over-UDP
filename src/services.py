import hashlib
import colorlog
from time import time

MSG_SEND: str = ".msg"
MSG_RECV: str = ".msg"


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


def sha256_file(file_path: str) -> bytes:
    BLOCKSIZE = 65536
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
        return hasher.digest()


formatter: colorlog.ColoredFormatter = colorlog.ColoredFormatter(
    fmt="\x1b[2K%(log_color)-8s%(reset)s %(log_color)s%(message)s%(reset)s\r",
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
    reset=True,
)
handler = colorlog.StreamHandler()
handler.setFormatter(formatter)
handler.terminator = '\r'

colorlog.getLogger('').addHandler(handler)

global log
log = colorlog.getLogger(__name__)
log.setLevel('DEBUG')
