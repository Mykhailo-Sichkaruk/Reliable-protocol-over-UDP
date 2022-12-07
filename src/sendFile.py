from math import ceil
from json import dumps
from enum import Enum
from typing import Callable
from packetParser import MRP, PacketType, create_packet


class SendState(Enum):
    Wait_init_confirm = 0
    Sending_window = 1


class SendFile:
    def __init__(self, id: int, send: Callable[[bytes], None], file_path: str, window_size: int = 8, frame_len: int = 2) -> None:
        self.id = id
        self.file_path = file_path
        self.window_size = window_size
        self.frame_len = frame_len
        self.state = SendState.Wait_init_confirm
        self.current_window = 0
        self.init_data = None
        self.init_data_windows = 0
        # self.file = open(file_path, "rb")
        self.send = send

    def run(self):
        if self.state == SendState.Wait_init_confirm:
            pass
        elif self.state == SendState.Sending_window:
            pass

    def get_window(self):
        window: list[bytes] = []
        for _i in range(self.window_size):
            window.append(self.file.read(self.frame_len))

        return window

    def init_sending(self):
        # Create a JSON object with the file path and the length of the file
        init_data = bytes(dumps({
            "path": self.file_path,
            "len": self.frame_len,
        }), "utf-8")

        # Length of the JSON object in bytes
        init_data_len = len(init_data)
        # Whole number of packets needed to send the JSON object
        separate_packets = ceil(init_data_len / self.frame_len)
        # Whole number of windows needed to send the JSON object
        window_amount = ceil(separate_packets / self.window_size)

        if window_amount > 255:
            raise Exception("Too many windows needed to send init data")

        self.init_data = init_data
        self.init_data_windows = window_amount

        self.send(create_packet(
            PacketType.Init_file_transfer, self.id, 0, 0, window_amount.to_bytes(1, "big")))


def main():
    file = SendFile(0, lambda x: print(x),
                    "C:\\Users\\micha\\Desktop\\test.txt")
    file.init_sending()


main()
