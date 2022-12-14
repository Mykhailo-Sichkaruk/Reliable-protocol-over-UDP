from zlib import crc32
from dataclasses import dataclass
from enum import Enum


class PacketType(Enum):
    Confirm = 5
    Data = 1
    ConfirmData = 9
    OpenConnection = 3
    ConfirmOpenConnection = 6
    Init_file_transfer = 11
    ConfirmInit_file_transfer = 12


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


def parse_first_byte(data: int):
    packet_type_number = data >> 4
    if packet_type_number < 0 or packet_type_number > 12:
        packet_type_number = 0
    packet_type = PacketType(packet_type_number)

    file_id = data & 0b00001111

    return packet_type, file_id


def parse_packet(data: bytes) -> MRP:
    """Parse bytes into MRP"""
    packet_type, file_id = parse_first_byte(data[0])
    packet_number_in_window = data[1]
    window_number = int.from_bytes(data[2:4], "big")
    checksum = int.from_bytes(data[4:8], "big")
    payload = data[8:]
    unbroken = check_checksum(data)

    return MRP(packet_type, file_id, packet_number_in_window, window_number, checksum, payload, unbroken)


def check_checksum(data: bytes) -> bool:
    """Check if checksum is correct"""
    checksum = int.from_bytes(data[4:8], "big")
    return checksum == crc32(data[0:4] + data[8:])


def create_packet(type: PacketType, file_id: int, number_in_window: int, window_number: int, payload: bytes) -> bytes:
    """Create MRP packet"""
    first_byte = (type.value << 4) + file_id
    packet_number_in_window = number_in_window.to_bytes(1, "big")
    packet_window_number = window_number.to_bytes(2, "big")
    checksum = crc32(bytes([first_byte]) + packet_number_in_window +
                     packet_window_number + payload).to_bytes(4, "big")

    return bytes([first_byte]) + packet_number_in_window + packet_window_number + checksum + payload
