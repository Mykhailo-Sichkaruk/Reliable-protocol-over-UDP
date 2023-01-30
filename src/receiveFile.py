import os

from services import sha256_file, time_ms, MSG_RECV, log
from enum import Enum
from typing import Callable
from packetParser import MRP, PacketType
from fileData import FileData


CONFIRM_RESEND_TIMEOUT = 5000  # ms
TRANSFER_TIMEOUT = 10000  # ms


class ReceiveState(Enum):
    Wait_window = 0
    Wait_init = 1
    End_transfer = 2


class ReceiveFile:
    def __init__(self, destination: tuple[str, int], send_function_injection: Callable[[bytes], None], packet: MRP | None = None) -> None:
        self.id: int = 0
        self.dst = f"{destination[0]}:{destination[1]}"
        self.send = send_function_injection
        self.window_size: int = 8
        self.fragment_len: int = 1
        self.init_data_raw = b""
        self.init_data_end_window: int = 0
        self.window: list[MRP] = []
        self.window_number: int = 0
        self.last_packet_time = time_ms()
        self.state = ReceiveState.Wait_init
        self.received_bytes: int = 0
        self.start_time: int = 0
        self.last_window_confirm: bytes = b""
        self.confirm_resend_time: int = 0
        self.inited = False
        self.window_timeout: int = 100
        self.size: int = 9999
        self.hash: str = ""
        self.path: str = ""

        if packet is not None:
            self.start_time = time_ms()
            self.add_packet(packet)

    def run(self):
        if (self.state == ReceiveState.Wait_window
                and self.last_packet_time + self.window_timeout < time_ms()):
            if self.inited and self.received_bytes < self.size:
                # Resend the last window
                if time_ms() - self.last_packet_time > TRANSFER_TIMEOUT:
                    self.handle_error_transfer()
                elif time_ms() - self.confirm_resend_time > self.window_timeout:
                    self.confirm_resend_time = time_ms()
                    self.handle_lost_packets()
            if not self.inited:
                pass
            else:
                self.end_transfer()

        return self.state != ReceiveState.End_transfer

    def handle_error_transfer(self):
        if self.path.endswith(MSG_RECV):
            log.warn(
                f"Message transfer failed <- {self.dst}\n")
        else:
            log.warn(
                f"{self.path} Receiving failed, host timed out <- {self.dst}\n")
        self.state = ReceiveState.End_transfer
        self.file.close()
        os.remove(self.path)

    def end_transfer(self):
        end_time = time_ms()
        self.file.seek(0)
        sha256: str = sha256_file(self.path).hex()
        self.file.seek(0)
        if self.path.endswith(MSG_RECV):
            msg = self.file.read().decode("utf-8")
            # Delete the file
            self.file.close()
            os.remove(self.path)
            log.critical(
                f"{self.dst}<<<< {msg}\n")
        else:
            if self.size > self.received_bytes:
                self.handle_error_transfer()
                return
            log.critical(
                f"\nFile received successfully <- {self.dst}\n\
                    \tFile: {self.path} \n\
                    \tFragment size: {self.fragment_len} B \n\
                    \tWindow size: {self.window_size} \n\
                    \tSHA256 expected: {self.hash} \n\
                    \tSHA256 received: {sha256} \n\
                    \tTime: {int((time_ms() - self.start_time) / 1000)}s \n\
                    \tFile size: {self.size} B \n\
                    \tAverage speed {int(self.size/ (end_time - self.start_time)) } KiB/s\n")
            self.file.close()

        self.state = ReceiveState.End_transfer

    def handle_window(self):
        if len(self.window) == self.window_size:
            if self.window_number < self.init_data_end_window:
                # Receive init datafile
                self.handle_init_window()
            elif self.window_number == self.init_data_end_window:
                self.handle_init_window()
                # Parse the init data
                file_data: FileData = FileData(data=self.init_data_raw)
                self.size = file_data.size
                self.hash = file_data.hash
                self.path = file_data.path
                self.inited = True
                try:
                    self.file = open(self.path, "wb+")
                except Exception as e:
                    log.critical(f"Error opening file: {e}")
                    self.handle_error_transfer()
                    return
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
                self.window.clear()
                return

        # Write the data to the file
        for packet in self.window:
            self.file.write(packet.payload)
            self.received_bytes += len(packet.payload)

        log.debug(
            f"F:{self.id} W:{self.window_number}: {round((self.received_bytes / self.size) * 100, 2)}% <-\t{self.dst}")
        # Send the confirm
        confirm_payload = ((2 ** self.window_size) -
                           1).to_bytes(self.window_size // 8, "big")
        self.send(MRP.serialize(PacketType.ConfirmData,
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
                raise ValueError("Window is not correct")

        # Add the data to the init data
        for packet in self.window:
            self.init_data_raw += packet.payload

        # Send the confirm
        confirm_payload = ((2 ** self.window_size) -
                           1).to_bytes(self.window_size // 8, "big")
        self.send(MRP.serialize(PacketType.ConfirmData,
                  self.id, 0, self.window_number, confirm_payload))

        self.last_window_confirm = confirm_payload
        self.window_number += 1
        self.window = []

    def handle_lost_packets(self):
        if self.last_window_confirm != b"":
            # Resend the last confirm
            self.send(MRP.serialize(PacketType.ConfirmData,
                      self.id, 0, self.window_number - 1, self.last_window_confirm))
            log.critical(
                f"F:{self.id} W:{self.window_number} Resend confirm <- {self.dst}\n")
        else:
            self.window.sort(key=lambda packet: packet.number_in_window)
            payload = self.get_sum_confirm()
            packet = MRP.serialize(
                PacketType.ConfirmData, self.id, 0, self.window_number, payload)
            self.send(packet)

    def get_sum_confirm(self) -> bytes:
        result = 0
        for packet in self.window:
            result |= 1 << (self.window_size - packet.number_in_window - 1)
        let = result.to_bytes(self.window_size // 8, "big")
        if len(let) != self.window_size // 8:
            raise ValueError("Wrong size")

        return let

    def add_packet(self, packet: MRP):
        self.last_packet_time = time_ms()
        if self.state == ReceiveState.Wait_init and packet.type == PacketType.Init_file_transfer:
            self.init_data_end_window = int.from_bytes(
                packet.payload, "big")
            self.id = packet.transfer_id
            self.window_size = packet.number_in_window
            self.fragment_len = packet.window_number
            self.window_timeout = (
                self.window_size * self.fragment_len**2) // 700000
            if self.window_timeout < 100:
                self.window_timeout = 100
            self.state = ReceiveState.Wait_window
            self.send(MRP.serialize(
                PacketType.ConfirmInit_file_transfer, self.id, 0, 0, b""))
        elif self.state == ReceiveState.Wait_window:
            self.window.append(packet)
            self.handle_window()

    def rename_file(self, full_name: str):
        postfix = full_name.split('.')[-1]
        # Remove / and . from the full name
        # Get onle the file name
        file_name = full_name.replace(
            '/', '!').replace('.', '!').replace(' ', '')
        # Delete all text till the last !
        file_name = file_name.split('!')[-1]

        return f'./src/save/!{file_name}!.{postfix}'

    def close(self):
        if self.size > self.received_bytes:
            self.handle_error_transfer()
        else:
            log.warn(f"File transfer complete {self.path}\n")
        self.file.close()
        self.state = ReceiveState.End_transfer
        self.last_packet_time = time_ms()
