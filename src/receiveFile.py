from collections import deque
from enum import Enum
from typing import Callable
from packetParser import MRP, PacketType


class ReceiveState(Enum):
    Wait_window = 0
    Wait_lost_packets = 1
    Wait_next_window = 2
    Wait_init = 3
    Wait_init_window = 4
    Wait_init_lost_packets = 5


class ReceiveFile:
    def __init__(self, file_path: str, self_function_injection: Callable[[bytes], None], window_size: int, fragment_len: int) -> None:
        self.send = self_function_injection
        self.packet_queue: deque[MRP] = deque()
        self.window_size = window_size

        self.state = ReceiveState.Wait_init

    def run(self):
        if self.state == ReceiveState.Wait_init:
            packet = self.find_packet(PacketType.Init_file_transfer)
            if packet != None:
                self.packet_queue.remove(packet)
                self.handle_init(packet)

    def add_packet(self, packet: MRP):
