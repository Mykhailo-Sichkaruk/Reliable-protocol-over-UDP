from collections import deque
from enum import Enum
from socket import SocketType
from services import time_ms, log
from packetParser import MRP, PacketType, create_packet
from receiveFile import ReceiveFile
from sendFile import SendFile

ACK_TIMEOUT = 100  # ms
KEEP_ALIVE_TIMEOUT = 10000  # ms


class ConnState(Enum):
    Disconnected = 1

    Send_awailable = 2
    Receive_awailable = 3

    Send_Receive_awailable = 4

    Wait_Send_Confirm = 0
    Wait_Send_awailable = 5

    Receive_Wait_Send_awailable = 6
    Receive_Wait_Send_Confirm = 7
    Wait_Receive_awailable = 8


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
        self.future_send: bool = False
        self._killed = False
        log.critical(f"Connection created with {ip}:{port}")

    def run(self):
        if self._killed:
            return False

        # Check for timeout
        if self.state == ConnState.Disconnected and not self.future_send:
            return False

        if time_ms() - self.last_packet_time > KEEP_ALIVE_TIMEOUT:
            self.handle_timeout()
        else:
            if self.state == ConnState.Wait_Send_Confirm:
                self.handle_send_confirm()
            elif self.state == ConnState.Wait_Send_awailable or self.state == ConnState.Receive_Wait_Send_awailable:
                self.handle_wait_send_awailable()
            else:
                delete_transfers = []
                for transfer in self.transfers.values():
                    if not transfer.run():
                        delete_transfers.append(transfer.id)

                for transfer_id in delete_transfers:
                    del self.transfers[transfer_id]
                    self.future_send = False

        return True

    def handle_timeout(self):
        if self.state == ConnState.Send_awailable or self.state == ConnState.Send_Receive_awailable:
            log.info("Long time no see, may I continue sending?")
            self.last_packet_time = time_ms()
            self.send(create_packet(
                PacketType.OpenConnection, 0, 0, 0, b""))
            if self.state == ConnState.Send_awailable:
                self.state = ConnState.Wait_Send_Confirm
            else:
                self.state = ConnState.Receive_Wait_Send_Confirm
        elif self.state == ConnState.Wait_Send_Confirm or self.state == ConnState.Receive_Wait_Send_Confirm:
            log.info(f"Disconnected from {self.destination} by timeout")
            self.state = ConnState.Disconnected
            return False

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
            log.warn("Packet is broken")
            return

        if packet.type == PacketType.OpenConnection:
            if self.state == ConnState.Disconnected:
                self.send(create_packet(
                    PacketType.ConfirmOpenConnection, 0, 0, 0, b""))
                self.state = ConnState.Wait_Receive_awailable
            elif self.state == ConnState.Send_awailable:
                self.send(create_packet(
                    PacketType.ConfirmOpenConnection, 0, 0, 0, b""))
                self.state = ConnState.Send_Receive_awailable
            else:
                self.send(create_packet(
                    PacketType.ConfirmOpenConnection, 0, 0, 0, b""))
        elif packet.type == PacketType.ConfirmOpenConnection:
            self.state = ConnState.Send_awailable
        elif self.state == ConnState.Wait_Receive_awailable:
            self.state = ConnState.Receive_awailable
            self.dispatch_packet(packet)
        elif self.state == ConnState.Receive_awailable or self.state == ConnState.Send_Receive_awailable or self.state == ConnState.Send_awailable:
            self.dispatch_packet(packet)
        else:
            raise ConnectionError(
                f"Packet {packet.type} received in state {self.state}")

    def dispatch_packet(self, packet: MRP):
        if packet.file_id not in self.transfers:
            self.transfers[packet.file_id] = ReceiveFile(self.destination,
                                                         self.send, packet)
        else:
            self.transfers[packet.file_id].add_packet(packet)

    def send(self, data: bytes):
        self.socket.sendto(data, self.destination)

    def send_file(self, file_path: str, frame_len: int, window_len: int):
        if self.state == ConnState.Send_awailable or self.state == ConnState.Send_Receive_awailable:
            self.transfers[self.last_transfer_id] = SendFile(self.destination,
                                                             self.last_transfer_id, self.send, file_path, window_len, frame_len)
        else:
            self.open_connection()
            self.future_send = True
            self.transfers[self.last_transfer_id] = SendFile(self.destination,
                                                             self.last_transfer_id, self.send, file_path, window_len, frame_len)

        self.last_transfer_id += 1

    def kill(self):
        self.state = ConnState.Disconnected
        self._killed = True
        log.critical(
            f"Connection with {self.destination[0]}:{self.destination[1]} killed")

    def close(self):
        self.state = ConnState.Disconnected
