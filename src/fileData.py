import os
from services import sha256_file


class FileData():
    """Class for creating the init data for the file transfer
    `file_len:  8B      ` - Length of the file in bytes
    `hash:      32B     ` - hash of the file
    `file_path: 0-255B  ` - Path of the file
    """

    def __init__(self, *, path: None | str = None, data: None | bytes = None) -> None:
        if path is not None:
            if not os.path.isfile(path):
                raise FileNotFoundError("File does not exist")
            if not os.access(path, os.R_OK):
                raise PermissionError("File is not readable")

            self.__size: bytes = os.path.getsize(
                path).to_bytes(8, "big")  # 8B
            self.__hash: bytes = sha256_file(path)  # 32B
            self.__path: bytes = self.filter_name(path)  # 0-255B
            self.raw: bytes = self.__size + self.__hash + self.__path
        elif data is not None:
            # Parse the init data
            self.__size: bytes = data[:8]
            self.__hash: bytes = data[8:40]
            self.__path: bytes = data[40:]
            self.raw: bytes = data
        else:
            raise ValueError("No data or path provided")

    @property
    def hash(self) -> str:
        return self.__hash.hex()

    @property
    def size(self) -> int:
        return int.from_bytes(self.__size, "big")

    @property
    def path(self) -> str:
        return self.__path.decode("utf-8")

    def __len__(self) -> int:
        return len(self.raw)

    def filter_name(self, path: str) -> bytes:
        """ Return the basename of the file from the path with the extension """
        return os.path.basename(path).encode(encoding="utf-8")


FileData(data=b'')
