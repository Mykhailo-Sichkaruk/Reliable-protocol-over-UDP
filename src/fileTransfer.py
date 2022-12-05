from collections import deque
from enum import Enum


class Direction(Enum):
    Send = 0
    Receive = 1


class FTState(Enum):
    Wait_window = 0
    Wait_window_confirm = 1
    Received_window = 2


class FileTransfer:
    def __init__(self, direction: Direction):
    self.packet_queue = deque()
    self.direction = Direction.Send
