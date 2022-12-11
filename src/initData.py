import hashlib
import colorlog
import os

from services import formatter

handler = colorlog.StreamHandler()
handler.setFormatter(formatter)
log = colorlog.getLogger(__name__)
log.addHandler(handler)


class InitData:
    """Class for creating the init data for the file transfer

    file_len:  8B,      Length of the file in bytes
    md5_hash:  16B,     MD5 hash of the file
    file_path: 0-255B   Path of the file
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.__len: int = 0
        # Try to open the file to check if it exists
        try:
            self.file = open(file_path, "rb")
            # Get the length of the file
            self.file_len = os.path.getsize(file_path)
            # Calculate md5 hash of the file
            self.hash = hashlib.md5(self.file.read()).digest()

            self.file.close()
        except FileNotFoundError:
            self.file.close()
            raise FileNotFoundError("File does not exist")

    @property
    def md5_hash(self) -> bytes:
        return self.hash

    @property
    def bytes(self) -> bytes:
        data = b''
        data += self.file_length.to_bytes(8, "big")
        data += self.hash
        data += bytes(self.file_path, "utf-8")

        self.__len = len(data)
        return data

    @property
    def file_len(self) -> int:
        return self.file_length

    @file_len.setter
    def file_len(self, value: int) -> None:
        self.file_length = value

    def __len__(self) -> int:
        return self.__len
