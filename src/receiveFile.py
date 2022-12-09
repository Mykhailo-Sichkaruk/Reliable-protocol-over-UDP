from bitstring import BitArray
from services import time_ms
from enum import Enum
from typing import Callable
from packetParser import MRP, PacketType, create_packet
import logging

log = logging.getLogger(__name__)

WINDOW_TIMEOUT = 50  # ms


class ReceiveState(Enum):
    Wait_window = 0
    Wait_init = 3
    End_transfer = 4j


class ReceiveFile:
    def __init__(self, self_function_injection: Callable[[bytes], None], window_size: int, fragment_len: int, packet: MRP | None = None) -> None:
        self.send = self_function_injection
        self.window_size = window_size
        self.fragment_len = fragment_len
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
            log.warn(
                f"Window timeout: last packet received {time_ms() - self.last_packet_time} ms ago")
            if self.received_bytes < self.file_len:
                # Resend the last window
                self.last_packet_time = time_ms()
                self.handle_lost_packets()
            else:
                self.end_transfer()

        return self.state == ReceiveState.End_transfer

    def end_transfer(self):
        log.critical(
            f"{self.file_path} Transfer ended successfully \n\
                \tTime: {time_ms() - self.start_time} ms \n\
                \tFile size: {self.file_len} b \n\
                \tAverage speed {int(self.file_len / (time_ms() - self.start_time) * 1000) } B/ms")
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
                self.file = open(self.file_path, "wb")
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
            f"{self.window_number}: {self.received_bytes}/{self.file_len}")
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
            return

        self.window.sort(key=lambda packet: packet.number_in_window)

        payload = self.get_sum_confirm()
        packet = create_packet(
            PacketType.ConfirmData, self.id, 0, self.window_number, payload)
        self.send(packet)

        log.info(f"Resend window {self.window_number}: {payload}")

    def get_sum_confirm(self) -> bytes:
        result = 0
        number_of_lost_packets = self.window_size
        for packet in self.window:
            number_of_lost_packets -= 1
            result += packet.number_in_window ** 2
        let = result.to_bytes(self.window_size // 8, "big")
        if len(let) != self.window_size // 8:
            raise Exception("Wrong size")

        print(f"Lost packets: {number_of_lost_packets}")
        return let

    def add_packet(self, packet: MRP):
        self.last_packet_time = time_ms()
        if self.state == ReceiveState.Wait_init and packet.type == PacketType.Init_file_transfer:
            self.init_data_end_window = int.from_bytes(
                packet.payload, "big")
            self.id = packet.file_id
            self.state = ReceiveState.Wait_window
            self.send(create_packet(
                PacketType.ConfirmInit_file_transfer, self.id, 0, 0, b""))
        elif self.state == ReceiveState.Wait_window:
            self.window.append(packet)
            self.handle_window()

    def parse_init_data(self, data: bytes) -> dict:
        # Parse the init data
        file_len = int.from_bytes(data[:8], "big")
        file_path = data[8:].decode("utf-8")
        return {"file_len": file_len, "file_path": file_path}

    def rename_file(self, new_name: str):
        name, postfix = new_name.split(
            ".")[:-1], new_name.split(".")[-1]

        return ".".join(name) + f"_copy." + postfix
