from bitstring import BitArray
from collections import deque
from enum import Enum
from time import time
from fileAdapter import FileAdapter
from packetParser import MRP, PacketType, create_packet
from typing import Callable


CONFIRM_WAIT_TIME = 5
WINDOW_WAIT_TIME = 5


class Direction(Enum):
    Send = 0
    Receive = 1


class FTState(Enum):
    Wait_window = 0
    Wait_window_confirm = 1
    Received_window = 2
    End_transfer = 3
    Resend_lost_packets = 4
    Wait_lost_packets = 5
    Wait_next_window = 6


class FileTransfer:
    def __init__(self, direction: Direction, file: FileAdapter, send_function_injection: Callable[[bytes], None], packet: MRP | None = None):
        self.send = send_function_injection
        self.packet_queue: deque[MRP] = deque()
        self.direction = direction
        self.file = file
        self.window_size = 8
        self.current_window: list[bytes] | None = []
        self.last_packet_time = time()
        self.window_first_packet_time = time()
        self.last_packet = None

        if packet != None and self.direction == Direction.Send:
            self.packet_queue.append(packet)
            self.state = FTState.Wait_window
        else:
            self.send_next_window()
            self.state = FTState.Wait_window_confirm

    def run(self):
        if self.direction == Direction.Send:
            self.run_send()
        else:
            self.run_receive()

    def run_send(self):
        if self.state == FTState.Wait_window_confirm:
            packet = self.find_packet(PacketType.Confirm)
            if packet != None:
                self.packet_queue.remove(packet)
                self.handle_confirm(packet)
        elif self.state == FTState.Wait_window:
            packet = self.find_packet(PacketType.Confirm)
            if packet != None:
                self.packet_queue.remove(packet)
                self.handle_confirm(packet)
        elif self.state == FTState.Wait_next_window:
            self.send_next_window()
            self.state = FTState.Wait_window_confirm
        else:
            raise Exception(f"Invalid state: {self.state}")

    def handle_confirm(self, packet: MRP):
        is_window_full = True
        confirm = packet.payload
        # Check summarized confirm
        if len(confirm)*8 != self.window_size:
            raise Exception("Summarized confirm != window size")
        else:
            for index, bit in enumerate(BitArray(bytes=confirm).bin):
                if bit == "0":
                    # Resend lost packet
                    is_window_full = False
                    self.send(create_packet(
                        PacketType.Data, self.current_window[index], index, self.file.id))
                    self.state = FTState.Resend_lost_packets

            if is_window_full:
                self.state = FTState.Wait_window_confirm
                self.send_next_window()
            else:
                self.state = FTState.Wait_window_confirm

    def send_next_window(self):
        self.current_window = self.file.get_next_window() or []
        for index, fragment in enumerate(self.current_window):
            self.send(create_packet(PacketType.Data,
                      fragment, index, self.file.id))

    def run_receive(self):
        print(f"Running receive with state: {self.state}")
        if self.state == FTState.Wait_window:
            self.wait_window()
        elif self.state == FTState.Wait_next_window:
            self.wait_next_window()
        else:
            raise Exception(f"Invalid state: {self.state}")

    def wait_next_window(self):
        if self.last_packet_time + WINDOW_WAIT_TIME < time():
            # Resend last packet
            self.send(self.last_packet)

    def wait_window(self):
        # Check if window is full
        print("Waiting for window")
        if len(self.packet_queue) == self.window_size:
            window = list(self.packet_queue.copy())
            # Sort packets by index
            window.sort(key=lambda packet: packet.packet_number)
            # Check if packets are in order
            for index, packet in enumerate(window):
                if packet.packet_number != index:
                    raise Exception("Packets are not in order")
            # Send Confirm packet
            self.packet_queue.clear()
            self.file.put_next_window(window)
            self.last_packet = create_packet(PacketType.Confirm, bytes(
                [self.window_size]), self.file.id)
            self.send(self.last_packet)
            self.last_packet_time = time()
            self.state = FTState.Wait_next_window
        elif time() - self.window_first_packet_time > WINDOW_WAIT_TIME:
            # Send early confirm
            # Check what packets are missing
            window = list(self.packet_queue.copy())
            window.sort(key=lambda packet: packet.packet_number)
            result = 0
            for index, packet in enumerate(window):
                # Check if packet is missing
                result += packet.packet_number ** 2

            self.last_packet = create_packet(PacketType.Confirm, result.to_bytes(
                self.window_size // 8, "big"), self.file.id)
            self.send(self.last_packet)
            self.last_packet_time = time()

    def find_packet(self, packet_type: PacketType):
        for packet in self.packet_queue:
            if packet.packet_type == packet_type:
                return packet

    def add_packet(self, packet: MRP):
        self.packet_queue.append(packet)
        self.last_packet_time = time()
        if len(self.packet_queue) == 1:
            self.window_first_packet_time = time()
        if self.state == FTState.Wait_next_window:
            self.state = FTState.Wait_window
