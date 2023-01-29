from random import randint
from zlib import crc32
from dataclasses import dataclass
from enum import Enum


FLAGS_BYTES: int = 1
"""Number of bytes for flags"""
PACKET_NUMBER_B: int = 1
"""Number of bytes for packet number"""
WINDOW_SIZE_B: int = 4
"""Number of bytes for window size"""
MAX_WINDOW_NUMBER: int = 2 ** (WINDOW_SIZE_B * 8) - 1
"""Maximum number of the window"""


class PacketType(Enum):
    Data = 1
    Confirm = 2
    ConfirmData = 3
    OpenConnection = 4
    ConfirmOpenConnection = 5
    Init_file_transfer = 6
    ConfirmInit_file_transfer = 7


@dataclass
class MRP:
    """Mykhailo's reliable protocol"""
    type: PacketType
    transfer_id: int
    number_in_window: int
    """Number of the packet inside the window from `0` to `window_size - 1`"""
    window_number: int
    payload: bytes

    @staticmethod
    def deserialize(data: bytes):
        """Parse bytes into MRP"""
        flags = data[0:(FLAGS_BYTES)]
        packet_type, file_id = MRP.parse_flags(flags)
        packet_number: int = int.from_bytes(data[FLAGS_BYTES:(FLAGS_BYTES +
                                                              PACKET_NUMBER_B)], "big")
        window_number = int.from_bytes(
            data[(FLAGS_BYTES+PACKET_NUMBER_B):+(FLAGS_BYTES+PACKET_NUMBER_B+WINDOW_SIZE_B)], "big")
        payload = data[(FLAGS_BYTES+PACKET_NUMBER_B +
                        WINDOW_SIZE_B):]

        return MRP(packet_type, file_id, packet_number, window_number, payload)

    @staticmethod
    def parse_flags(data: bytes) -> tuple[PacketType, int]:
        flags = int.from_bytes(data, "big")
        packet_type_number = flags >> 4
        if packet_type_number < 0 or packet_type_number > 12:
            packet_type_number = 0
        packet_type = PacketType(packet_type_number)

        file_id = flags & 0b00001111

        return packet_type, file_id

    @ staticmethod
    def check_checksum(data: bytes) -> bool:
        """Check if checksum is correct"""
        checksum = int.from_bytes(data[4:8], "big")
        return checksum == crc32(data[0:4] + data[8:])

    @ staticmethod
    def serialize(type: PacketType, file_id: int, number_in_window: int, window_number: int, payload: bytes) -> bytes:
        """Create MRP packet"""
        first_byte: int = (type.value << 4) + file_id
        packet_number_in_window = number_in_window.to_bytes(
            PACKET_NUMBER_B, "big")
        packet_window_number = window_number.to_bytes(
            WINDOW_SIZE_B, "big")

        return bytes([first_byte]) + packet_number_in_window + packet_window_number + payload

    @ staticmethod
    def broke_packet(data: bytes):
        # Change any byte in the packet
        random_index = randint(0, len(data) - 1)
        bytearray_data = bytearray(data)
        bytearray_data[random_index] = randint(0, 255)

        return bytes(bytearray_data)
