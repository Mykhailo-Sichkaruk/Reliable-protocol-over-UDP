from hashlib import md5
from bitstring import BitArray
from services import time_ms
from enum import Enum
from typing import Callable
from packetParser import MRP, PacketType, create_packet
import logging

log = logging.getLogger(__name__)

WINDOW_TIMEOUT = 500  # ms


class ReceiveState(Enum):
    Wait_window = 0
    Wait_init = 3
    End_transfer = 4j


class ReceiveFile:
    def __init__(self, self_function_injection: Callable[[bytes], None], packet: MRP | None = None) -> None:
        self.send = self_function_injection
        self.window_size: int = 8
        self.fragment_len: int = 1
        self.init_data = b""
        self.init_data_end_window: int = 0
        self.window: list[MRP] = []
        self.window_number: int = 0
        self.last_packet_time = time_ms()
        self.state = ReceiveState.Wait_init
        self.received_bytes: int = 0
        self.id: int = 0
        self.is_started: bool = False
        self.start_time: int = 0
        self.last_window_confirm: bytes = b""

        if packet is not None:
            self.start_time = time_ms()
            self.is_started = True
            self.add_packet(packet)

        log.critical(f"Receiving file")

    def run(self):
        if (self.state == ReceiveState.Wait_window
                and self.last_packet_time + WINDOW_TIMEOUT < time_ms()):
            if self.received_bytes < self.file_len:
                # Resend the last window
                self.last_packet_time = time_ms()
                self.handle_lost_packets()
            else:
                self.end_transfer()

        return self.state == ReceiveState.End_transfer

    def end_transfer(self):
        end_time = time_ms()
        self.file.seek(0)
        hash = md5(self.file.read()).hexdigest()
        log.critical(
            f"Transfer ended successfully \n\
                \tFile: {self.file_path} \n\
                \tFragment size: {self.fragment_len} B \n\
                \tWindow size: {self.window_size} \n\
                \tMD5 hash expected: {self.md5_hash_expected} \n\
                \tMD5 Hash received: {hash} \n\n\
                \tTime: {int((time_ms() - self.start_time) / 1000)}s \n\
                \tFile size: {self.file_len} B \n\
                \tAverage speed {int(self.file_len / (end_time - self.start_time)) } KiB/s")
        self.file.close()
        self.state = ReceiveState.End_transfer

    def handle_window(self):
        if len(self.window) == self.window_size:
            if self.window_number < self.init_data_end_window:
                # Receive init data
                self.handle_init_window()
            elif self.window_number == self.init_data_end_window:
                self.handle_init_window()
                # Parse the init data
                data = self.parse_init_data(self.init_data)
                self.file_len = int(data["file_len"])
                self.file_path = self.rename_file(data["file_path"])
                self.md5_hash_expected: str = data["md5_hash"].hex()
                self.file = open(self.file_path, "wb+")
            else:
                # Receive file data/
                self.handle_file_window()
        else:
            self.last_window_confirm = b""

    def handle_file_window(self):
        # Sort the packets
        self.window.sort(key=lambda x: x.number_in_window)
        # Check if the window is correct
        for i in range(self.window_size):
            if self.window[i].number_in_window != i:
                raise Exception(
                    f"Window is not correct {self.window_number} {i}!={self.window[i].number_in_window}")

        # Write the data to the file
        for packet in self.window:
            self.file.write(packet.payload)
            self.received_bytes += len(packet.payload)

        log.debug(
            f"F:{self.id} W:{self.window_number}: {round((self.received_bytes / self.file_len) * 100, 2)}%")
        # Send the confirm
        confirm_payload = ((2 ** self.window_size) -
                           1).to_bytes(self.window_size // 8, "big")
        self.send(create_packet(PacketType.ConfirmData,
                  self.id, 0, self.window_number, confirm_payload))

        self.last_window_confirm = confirm_payload
        self.window_number += 1
        self.window = []

    def handle_init_window(self):
        # Sort the packets
        self.window.sort(key=lambda x: x.number_in_window)
        # Check if the window is correct
        for i in range(self.window_size):
            if self.window[i].number_in_window != i:
                raise Exception("Window is not correct")

        # Add the data to the init data
        for packet in self.window:
            self.init_data += packet.payload

        # Send the confirm
        confirm_payload = ((2 ** self.window_size) -
                           1).to_bytes(self.window_size // 8, "big")
        self.send(create_packet(PacketType.ConfirmData,
                  self.id, 0, self.window_number, confirm_payload))

        self.last_window_confirm = confirm_payload
        self.window_number += 1
        self.window = []

    def handle_lost_packets(self):
        if self.last_window_confirm != b"":
            # Resend the last confirm
            self.send(create_packet(PacketType.ConfirmData,
                      self.id, 0, self.window_number - 1, self.last_window_confirm))
            log.critical(
                f"Resend confirm {self.window_number}: {self.last_window_confirm}")
        else:
            self.window.sort(key=lambda packet: packet.number_in_window)

            payload = self.get_sum_confirm()
            packet = create_packet(
                PacketType.ConfirmData, self.id, 0, self.window_number, payload)
            self.send(packet)

    def get_sum_confirm(self) -> bytes:
        result = 0
        for packet in self.window:
            result |= 1 << (self.window_size - packet.number_in_window - 1)
        let = result.to_bytes(self.window_size // 8, "big")
        if len(let) != self.window_size // 8:
            raise Exception("Wrong size")

        return let

    def add_packet(self, packet: MRP):
        if self.state == ReceiveState.Wait_init and packet.type == PacketType.Init_file_transfer:
            self.init_data_end_window = int.from_bytes(
                packet.payload, "big")
            self.id = packet.file_id
            self.window_size = packet.number_in_window
            self.fragment_len = packet.window_number
            self.state = ReceiveState.Wait_window
            log.info(f"Init transfer, time: {time_ms()}")
            self.send(create_packet(
                PacketType.ConfirmInit_file_transfer, self.id, 0, 0, b""))
        elif self.state == ReceiveState.Wait_window:
            self.window.append(packet)
            self.handle_window()
        self.last_packet_time = time_ms()

    def parse_init_data(self, data: bytes) -> dict:
        # Parse the init data
        log.debug(f"Init data: {data}")
        file_len = int.from_bytes(data[:8], "big")
        md5_hash = data[8:24]
        file_path = data[24:].decode("utf-8")
        return {"file_len": file_len, "md5_hash": md5_hash, "file_path": file_path}

    def rename_file(self, new_name: str):
        name, postfix = new_name.split(
            ".")[:-1], new_name.split(".")[-1]

        return ".".join(name) + f"_copy." + postfix
