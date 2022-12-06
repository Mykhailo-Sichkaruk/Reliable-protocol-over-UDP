from bitstring import Bits
from zlib import crc32
from dataclasses import dataclass
from enum import Enum


class PacketType(Enum):
    Message = 0
    Data = 1
    KeepAlive = 2
    OpenConnection = 3
    CloseConnection = 4
    Confirm = 5
    ConfirmOpenConnection = 6
    ConfirmCloseConnection = 7
    ConfirmKeepAlive = 8


@dataclass
class MRP:
    """Mykhailo's reliable protocol"""
    packet_type: PacketType
    length: int
    checksum: int
    packet_number: int
    file_id: int
    payload: bytes
    unbroken: bool


def parse_MRP(data: bytes) -> MRP:
    """Parse bytes into MRP"""
    packet_type = parse_packet_type(data[0])
    length = parse_length(data[0:2])
    checksum = int.from_bytes(data[2:6], "big")
    unbroken = check_integrity(data)
    payload = data[8:]
    packet_number = int.from_bytes(data[7:8], "big")
    file_id = int.from_bytes(data[6:7], "big")

    return MRP(packet_type, length, checksum, packet_number, file_id, payload, unbroken)


def parse_packet_type(data: int) -> PacketType:
    """Parse header bytes into PacketType"""
    return PacketType(data >> 4)


def parse_length(data: bytes) -> int:
    """Parse header bytes into length"""
    return int(data[0] << 8 | data[1])


def check_integrity(data: bytes) -> bool:
    """Check if data is corrupted"""
    packet = data[0:2] + data[6:]
    checksum = int.from_bytes(data[2:6], "big")
    packet_checksum = crc32(packet)

    return checksum == packet_checksum


def create_packet(packet_type: PacketType, payload=b"", packet_number=0, file_id=0) -> bytes:
    """Create MRP packet from data"""
    length = len(payload)

    header = int(length | (packet_type.value << 12)).to_bytes(2, "big")
    print(f"{packet_type} N:{packet_number} F:{file_id} L:{length} P:{payload.hex()}")
    verify = header + \
        packet_number.to_bytes(1, "big") + file_id.to_bytes(1, "big")

    checksum = crc32(verify).to_bytes(4, "big")

    return header + checksum + packet_number.to_bytes(1, "big") + file_id.to_bytes(1, "big") + payload


def test_create_packet():
    print(create_packet(PacketType.Message, b"Hello, world"))
    # print(Bits(bytes=create_packet(PacketType.Message, b"Hello, world")))


def test_checksum():
    packet = create_packet(PacketType.Message, b"Hello, world")
    print(check_integrity(packet))


test_checksum()
