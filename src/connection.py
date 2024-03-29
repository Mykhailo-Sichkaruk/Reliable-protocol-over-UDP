from enum import Enum
from socket import SocketType
from services import time_ms, log
from packetParser import MRP, PacketType
from receiveFile import ReceiveFile
from sendFile import SendFile

ACK_TIMEOUT = 300  # ms
SENDER_KEEPALIVE_TIMEOUT = 11000  # ms
RECEIVED_KEEP_ALIVE_TIMEOUT = 21000  # ms


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
        self.last_transfer_id: int = 0
        self.future_send: bool = False
        self._killed = False
        log.critical(f"Connection created with {ip}:{port}\n")

    def run(self) -> bool:
        if self._killed:
            return False

        # Check for timeout
        if self.state == ConnState.Disconnected and not self.future_send:
            return False

        if time_ms() - self.last_packet_time > SENDER_KEEPALIVE_TIMEOUT:
            self.handle_timeout()
        else:
            if self.state == ConnState.Wait_Send_awailable or self.state == ConnState.Receive_Wait_Send_awailable:
                self.handle_wait_send_awailable()
            else:
                delete_transfers: list[int] = []
                for transfer in self.transfers.values():
                    if not transfer.run():
                        delete_transfers.append(transfer.id)

                for transfer_id in delete_transfers:
                    del self.transfers[transfer_id]
                    self.future_send = False

        return True

    def handle_timeout(self):
        if self.state == ConnState.Send_awailable or self.state == ConnState.Send_Receive_awailable:
            log.info(
                f"{self.destination[0]}:{self.destination[1]}  Long time no see, may I continue sending?\n")
            self.last_packet_time = time_ms()
            self.send(MRP.serialize(
                PacketType.OpenConnection, 0, 0, 0, b""))
            if self.state == ConnState.Send_awailable:
                self.state = ConnState.Wait_Send_Confirm
            else:
                self.state = ConnState.Receive_Wait_Send_Confirm
        elif self.state == ConnState.Wait_Send_Confirm or self.state == ConnState.Receive_Wait_Send_Confirm:
            log.info(f"Disconnected from {self.destination} by timeout\n")
            self.state = ConnState.Disconnected
            return False
        elif self.state == ConnState.Receive_awailable or self.state == ConnState.Receive_Wait_Send_awailable:
            if self.last_packet_time + RECEIVED_KEEP_ALIVE_TIMEOUT < time_ms():
                if self.state == ConnState.Receive_awailable:
                    log.warn(
                        f"{self.destination[0]}:{self.destination[1]} Sender is not interested in sending, closing...\n")
                    self.state = ConnState.Disconnected
                else:
                    log.warn(
                        f"{self.destination[0]}:{self.destination[1]} Sender is not interested in sending, but can receive\n")
                    self.state = ConnState.Wait_Send_awailable

    def handle_wait_send_awailable(self):
        # If there are no packets for a long time, then resend the send confirmation
        if time_ms() - self.last_packet_time > ACK_TIMEOUT:
            self.send(MRP.serialize(
                PacketType.ConfirmOpenConnection, 0, 0, 0, b""))

    def open_connection(self):
        # Open sending stream
        if self.state == ConnState.Disconnected:
            self.state = ConnState.Wait_Send_Confirm
        elif self.state == ConnState.Receive_awailable:
            self.state = ConnState.Receive_Wait_Send_Confirm

        self.send(MRP.serialize(PacketType.OpenConnection, 0, 0, 0, b""))

    def add_packet(self, packet: MRP):
        self.last_packet_time = time_ms()

        if packet.type == PacketType.OpenConnection:
            if self.state == ConnState.Disconnected:
                self.send(MRP.serialize(
                    PacketType.ConfirmOpenConnection, 0, 0, 0, b""))
                self.state = ConnState.Wait_Receive_awailable
            elif self.state == ConnState.Send_awailable:
                self.send(MRP.serialize(
                    PacketType.ConfirmOpenConnection, 0, 0, 0, b""))
                self.state = ConnState.Send_Receive_awailable
            else:
                self.send(MRP.serialize(
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
        if packet.transfer_id not in self.transfers:
            # TODO: Ask user if he wants to receive this file
            self.transfers[packet.transfer_id] = ReceiveFile(self.destination,
                                                             self.send, packet)
            self.last_transfer_id += 1
        else:
            self.transfers[packet.transfer_id].add_packet(packet)

    def send(self, data: bytes):
        self.socket.sendto(data, self.destination)

    def send_file(self, file_path: str, frame_len: int, window_len: int):
        free_id: int | None = self.get_id()
        if free_id is None:
            log.error("No free id for transfer")
            return False

        if self.state == ConnState.Send_awailable or self.state == ConnState.Send_Receive_awailable:
            self.transfers[free_id] = SendFile(self.destination,
                                               free_id, self.send, file_path, window_len, frame_len)
        else:
            self.open_connection()
            self.future_send = True
            self.transfers[free_id] = SendFile(self.destination,
                                               free_id, self.send, file_path, window_len, frame_len)
        return True

    def get_id(self) -> int | None:
        # Return free id for transfer (0-15)
        for i in range(16):
            if i not in self.transfers:
                return i

    def kill(self):
        for transfer in self.transfers.values():
            transfer.close()
        self.state = ConnState.Disconnected
        self._killed = True

        log.warn(
            f"Forced close connection with {self.destination[0]}:{self.destination[1]}\n")

    def close(self):
        for transfer in self.transfers.values():
            transfer.close()
        self.state = ConnState.Disconnected
