from collections import deque
from enum import Enum
import logging
from socket import SocketType
from services import time_ms
from packetParser import MRP, PacketType, create_packet
from receiveFile import ReceiveFile
from sendFile import SendFile

ACK_TIMEOUT = 100  # ms
log = logging.getLogger(__name__)


class ConnState(Enum):
    Disconnected = 1

    Send_awailable = 2
    Receive_awailable = 3

    Send_Receive_awailable = 4

    Wait_Send_Confirm = 0
    Wait_Send_awailable = 5

    Receive_Wait_Send_awailable = 6
    Receive_Wait_Send_Confirm = 7


class Conn:
    def __init__(self, socket: SocketType, ip: str, port: int, window_size: int, frame_len: int) -> None:
        self.socket = socket
        self.destination: tuple[str, int] = (ip, port)
        self.state = ConnState.Disconnected
        self.receive_awailable: bool = False
        self.send_awailable: bool = False
        self.window_size: int = window_size
        self.frame_len: int = frame_len
        self.transfers: dict[int, ReceiveFile | SendFile] = {}
        self.last_packet_time: int = time_ms()  # ms
        self.packet_queue: deque[MRP] = deque()
        self.last_transfer_id: int = 0

        log.critical(f"Connection created with {ip}:{port}")

    def run(self):
        if self.state == ConnState.Wait_Send_Confirm:
            self.handle_send_confirm()
        elif self.state == ConnState.Wait_Send_awailable or self.state == ConnState.Receive_Wait_Send_awailable:
            self.handle_wait_send_awailable()
        else:
            for transfer in self.transfers.values():
                transfer.run()

        return self.state != ConnState.Disconnected

    def handle_wait_send_awailable(self):
        # If there are no packets for a long time, then resend the send confirmation
        if time_ms() - self.last_packet_time > ACK_TIMEOUT:
            self.send(create_packet(
                PacketType.ConfirmOpenConnection, 0, 0, 0, b""))

    def handle_send_confirm(self):
        if self.find_packet(PacketType.Confirm) != None:
            self.state = ConnState.Send_awailable

    def open_connection(self):
        # Open sending stream
        if self.state == ConnState.Disconnected:
            self.state = ConnState.Wait_Send_Confirm
        elif self.state == ConnState.Receive_awailable:
            self.state = ConnState.Receive_Wait_Send_Confirm

        self.send(create_packet(PacketType.OpenConnection, 0, 0, 0, b""))

    def find_packet(self, packet_type: PacketType):
        for packet in self.packet_queue:
            if packet.type == packet_type:
                return packet

    def add_packet(self, packet: MRP):
        self.last_packet_time = time_ms()

        if not packet.unbroken:
            return

        if packet.type == PacketType.OpenConnection:
            if self.state == ConnState.Disconnected:
                self.send(create_packet(
                    PacketType.ConfirmOpenConnection, 0, 0, 0, b""))
                self.state = ConnState.Wait_Send_awailable
            elif self.state == ConnState.Send_awailable:
                self.send(create_packet(
                    PacketType.ConfirmOpenConnection, 0, 0, 0, b""))
                self.state = ConnState.Send_Receive_awailable
        elif packet.type == PacketType.ConfirmOpenConnection and self.state == ConnState.Wait_Send_Confirm:
            self.state = ConnState.Send_awailable
        elif self.state == ConnState.Wait_Send_awailable:
            self.state = ConnState.Send_awailable
            self.dispatch_packet(packet)
        elif self.state == ConnState.Receive_awailable or self.state == ConnState.Send_Receive_awailable or self.state == ConnState.Send_awailable:
            self.dispatch_packet(packet)
        else:
            raise Exception(
                f"Packet {packet.type} received in state {self.state}")

    def dispatch_packet(self, packet: MRP):
        if packet.file_id not in self.transfers:
            self.transfers[packet.file_id] = ReceiveFile(
                self.send, packet)
        else:
            self.transfers[packet.file_id].add_packet(packet)

    def send(self, data: bytes):
        self.socket.sendto(data, self.destination)

    def send_file(self, file_path: str, frame_len: int, window_len: int):
        if self.state == ConnState.Send_awailable or self.state == ConnState.Send_Receive_awailable:
            self.transfers[self.last_transfer_id] = SendFile(
                self.last_transfer_id, self.send, file_path, window_len, frame_len)
        else:
            self.open_connection()
            self.transfers[self.last_transfer_id] = SendFile(
                self.last_transfer_id, self.send, file_path, window_len, frame_len)
