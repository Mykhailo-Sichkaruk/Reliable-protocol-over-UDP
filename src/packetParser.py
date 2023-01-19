from zlib import crc32
from dataclasses import dataclass
from enum import Enum


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
    file_id: int
    number_in_window: int
    """Number of the packet inside the window from 0 to window_size - 1"""
    window_number: int
    checksum: int
    payload: bytes
    unbroken: bool

    @staticmethod
    def deserialize(data: bytes):
        """Parse bytes into MRP"""
        packet_type, file_id = MRP.parse_first_byte(data[0])
        packet_number_in_window = data[1]
        window_number = int.from_bytes(data[2:4], "big")
        checksum = int.from_bytes(data[4:8], "big")
        payload = data[8:]
        unbroken = MRP.check_checksum(data)

        return MRP(packet_type, file_id, packet_number_in_window, window_number, checksum, payload, unbroken)

    @staticmethod
    def parse_first_byte(data: int) -> tuple[PacketType, int]:
        packet_type_number = data >> 4
        if packet_type_number < 0 or packet_type_number > 12:
            packet_type_number = 0
        packet_type = PacketType(packet_type_number)

        file_id = data & 0b00001111

        return packet_type, file_id

    @staticmethod
    def check_checksum(data: bytes) -> bool:
        """Check if checksum is correct"""
        checksum = int.from_bytes(data[4:8], "big")
        return checksum == crc32(data[0:4] + data[8:])

    @staticmethod
    def serialize(type: PacketType, file_id: int, number_in_window: int, window_number: int, payload: bytes) -> bytes:
        """Create MRP packet"""
        first_byte = (type.value << 4) + file_id
        packet_number_in_window = number_in_window.to_bytes(1, "big")
        packet_window_number = window_number.to_bytes(2, "big")
        checksum = crc32(bytes([first_byte]) + packet_number_in_window +
                         packet_window_number + payload).to_bytes(4, "big")

        return bytes([first_byte]) + packet_number_in_window + packet_window_number + checksum + payload
