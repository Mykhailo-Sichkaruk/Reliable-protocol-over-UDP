import os

from math import ceil
from enum import Enum
from io import SEEK_END
from typing import Any, Callable
from initData import InitData
from packetParser import MRP, PacketType
from services import MSG_SEND, log


class SendState(Enum):
    Wait_init_confirm = 0
    Sending_window = 1
    Sending_lost_packets = 2
    Wait_window_confirm = 3
    End_transfer = 4


class SendFile:
    def __init__(self, destination: tuple[str, int], id: int, send: Callable[[bytes], None], file_path: str, window_size: int = 64, fragment_len: int = 100) -> None:
        self.destination = destination
        self.id = id
        self.file_path = file_path
        self.window_size = window_size
        self.fragment_len = fragment_len
        self.state = SendState.Wait_init_confirm
        self.send_window: list[bytes] | None = []
        self.window_number = 0
        self.init_data: bytes = b''
        self.init_last_window = 0
        self.send = send
        self.is_inited: bool = False
        self.md5_hash: bytes
        self.file: Any

    def run(self):
        if not self.is_inited:
            self.init()
            self.is_inited = True

        return self.state != SendState.End_transfer

    def init(self):
        try:
            self.file = open(self.file_path, "rb")
            self.__file_size = self.file.seek(0, SEEK_END)
            self.file.seek(0)
            self.send_file_init()
            if self.file_path != MSG_SEND:
                log.info(
                    f"Sending file:{self.id} {self.file_path}: {self.__file_size} bytes -> {self.destination[0]}:{self.destination[1]}")
            else:
                log.info(
                    f"Send msg with size {self.__file_size} bytes -> {self.destination[0]}:{self.destination[1]}")

        except Exception as e:
            log.error(f"Error opening file: {e}")
            self.state = SendState.End_transfer

    def get_window(self):
       # While cursore isnt at the end of the file, yield a window of data,
        if self.window_number <= self.init_last_window:
            # Send init data
            window_start = self.window_number * self.window_size * self.fragment_len
            window_end = window_start + self.window_size * self.fragment_len
            init_window = self.init_data[window_start:window_end]
            current_window: list[bytes] = []
            for i in range(0, len(init_window), self.fragment_len):
                current_window.append(init_window[i:i+self.fragment_len])
            if len(current_window) != self.window_size:
                # Fill the rest of the window with empty packets
                for _ in range(self.window_size - len(current_window)):
                    current_window.append(b'')

            return current_window
        elif self.file.tell() != self.__file_size:
            result = [self.file.read(self.fragment_len)
                      for _ in range(self.window_size)]

            return result

    def send_file_init(self):
        # Get the init data
        init_data: InitData = InitData(self.file_path)
        self.md5_hash = init_data.md5_hash
        self.init_data = init_data.bytes

        self.send_init(len(init_data))

    def send_init(self, init_data_len: int):
        # Whole number of packets needed to send the JSON object
        separate_packets = ceil(init_data_len / self.fragment_len)
        # Whole number of windows needed to send the JSON object
        window_amount = ceil(separate_packets / self.window_size)

        if window_amount > 255:
            raise ValueError("Too many windows needed to send init data")

        self.init_last_window = window_amount - 1
        # Send init packet with the amount of windows needed to send the InitData structure
        self.send(MRP.serialize(
            PacketType.Init_file_transfer, self.id, self.window_size, self.fragment_len, self.init_last_window.to_bytes(1, "big")))

    def send_next_window(self):
        # Update window
        self.send_window = self.get_window()
        if self.send_window is None:
            self.handle_end_transfer()
        else:
            for i, packet in enumerate(self.send_window):
                self.send(MRP.serialize(PacketType.Data, self.id,
                                        i, self.window_number, packet))

    def handle_end_transfer(self):
        self.file.close()
        if self.file_path != MSG_SEND:
            log.critical(f"File sent successfully -> {self.destination[0]}:{self.destination[1]}\n\
                                \tFile: {self.file_path}\n\
                                \tFragment size: {self.fragment_len}\n\
                                \tWindow size: {self.window_size}\n\
                                \tMD5 hash: {self.md5_hash.hex()}\n\n\
                                \tFile size: {self.__file_size}B")
        else:
            os.remove(self.file_path)

        self.state = SendState.End_transfer

    def add_packet(self, packet: MRP):
        if self.state == SendState.Wait_init_confirm:
            if packet.type == PacketType.ConfirmInit_file_transfer:
                self.state = SendState.Sending_window
                self.send_next_window()
                self.state = SendState.Wait_window_confirm
        elif self.state == SendState.Wait_window_confirm:
            if packet.type == PacketType.ConfirmData:
                self.handle_window_confirm(packet)

    def handle_window_confirm(self, packet: MRP):
        # Get the window number from the packet
        window_number = packet.window_number

        # If the window number is the same as the current window number
        if window_number == self.window_number:
            # Check if it confirms the whole window
            is_window_full = True
            confirm: bytes = packet.payload
            # Check summarized confirm
            # Every bit in the confirm is a packet in the window, 1 = received, 0 = not received
            # Check if all packets are received and resend the lost ones
            confirm_int = int.from_bytes(confirm, "big")
            for index in range(len(confirm)*8):
                bit = 1 << (self.window_size - index - 1)
                if (bit & confirm_int) == 0:
                    is_window_full = False
                    # Resend lost packet
                    if self.send_window is not None:
                        self.send(MRP.serialize(
                            PacketType.Data, self.id, index, self.window_number, self.send_window[index]))

            if is_window_full:
                self.state = SendState.Wait_window_confirm
                self.window_number += 1
                self.send_next_window()
            else:
                log.info(
                    f"F:{self.id} W:{self.window_number} resend some packets -> {self.destination[0]}:{self.destination[1]}")

    def close(self):
        self.file.close()
