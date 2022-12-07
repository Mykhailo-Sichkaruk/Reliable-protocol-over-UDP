from random import randint, random
from socket import SocketType
from fileAdapter import FileAdapter
from fileTransfer import Direction, FileTransfer
from collections import deque
from time import time
from packetParser import MRP, PacketType, create_packet
from enum import Enum


class ConnectionState(Enum):
    Disconnected = 0
    Connected = 1

    Connect_wait_confirm = 3
    Connect_wait_init = 4

    Disconnect_received = 5
    Disconnect_wait_confirm = 6
    Disconnect_wait_init = 7

    Time_exceeded = 8


class Connection:
    def __init__(self, socket: SocketType, ip, port, packet: MRP | None = None):
        self.keep_alive_time = 10  # seconds
        self.socket = socket
        self.ip = ip
        self.port = port
        self.packet_queque = deque()
        self.state = ConnectionState.Disconnected
        self.transfers = {}
        self.previous_state = ConnectionState.Disconnected
        self.last_packet_time = time()
        self.transfers: dict[int, FileTransfer] = {}

        self.will_send = True
        self.will_receive = True

        if packet == None:
            self.last_packet_time = 0
            self.init_handshake()
        else:
            self.last_packet_time = time()
            self.confirm_init_wait_confirm_handshake(packet)

    def confirm_init_wait_confirm_handshake(self, packet: MRP):
        self.socket.sendto(create_packet(
            PacketType.Confirm, b"", packet.packet_number, 0), (self.ip, self.port))
        self.socket.sendto(create_packet(
            PacketType.OpenConnection, b"", packet.packet_number, 0), (self.ip, self.port))
        self.state = ConnectionState.Connect_wait_confirm

    def init_handshake(self):
        self.socket.sendto(create_packet(
            PacketType.OpenConnection, b"", 0, 0), (self.ip, self.port))
        self.state = ConnectionState.Connect_wait_init

    def run(self):
        # Check if connection is alive
        if time() - self.last_packet_time > self.keep_alive_time:
            self.state = ConnectionState.Time_exceeded

        if self.state == ConnectionState.Disconnected:
            return ConnectionState.Disconnected
        elif self.state == ConnectionState.Connect_wait_confirm:
            self.wait_confirm()
        elif self.state == ConnectionState.Connect_wait_init:
            self.wait_init()
        elif self.state == ConnectionState.Disconnect_wait_confirm:
            self.disconnect_wait_confirm()
        else:
            # Run all transfers
            for transfer in self.transfers.values():
                transfer.run()

    def disconnect_wait_confirm(self):
        packet = self.find_packet_type(PacketType.Confirm)
        if packet != None:
            if packet.packet_type == PacketType.Confirm:
                self.state = ConnectionState.Disconnected

    def wait_init(self):
        print("Waiting for init")
        packet = self.find_packet_type(PacketType.OpenConnection)
        if packet != None:
            if packet.packet_type == PacketType.OpenConnection:
                self.socket.sendto(create_packet(
                    PacketType.Confirm, b"", packet.packet_number, 0), (self.ip, self.port))
                self.state = ConnectionState.Connected

    def wait_confirm(self):
        packet = self.find_packet_type(PacketType.Confirm)
        if packet != None:
            if packet.packet_type == PacketType.Confirm:
                self.socket.sendto(create_packet(
                    PacketType.Confirm, b"", packet.packet_number, 0), (self.ip, self.port))
                self.socket.sendto(create_packet(
                    PacketType.OpenConnection, b"", packet.packet_number, 0), (self.ip, self.port))

                self.state = ConnectionState.Connected

    def find_packet_type(self, packet_type: PacketType):
        for packet in self.packet_queque:
            if packet.packet_type == packet_type:
                return packet

    def add_packet(self, packet: MRP):
        self.last_packet_time = time()
        # If packet is Connect/Disconnect/KeepAlive related - add it to the queque
        print(
            f"<< {packet.packet_type} N:{packet.packet_number} F:{packet.file_id}: {packet.payload}")
        if packet.packet_type == PacketType.CloseConnection:
            self.will_receive = False
            self.socket.sendto(create_packet(
                PacketType.Confirm, b"", packet.packet_number, 0), (self.ip, self.port))
            if self.will_send == False:
                self.state = ConnectionState.Disconnected
        elif packet.packet_type == PacketType.ConfirmCloseConnection:
            self.will_send = False
            if self.will_receive == False:
                self.state = ConnectionState.Disconnected
        elif packet.packet_type == PacketType.OpenConnection:
            self.packet_queque.append(packet)
        elif packet.packet_type == PacketType.ConfirmOpenConnection:
            self.packet_queque.append(packet)
        elif packet.packet_type == PacketType.KeepAlive:
            self.packet_queque.append(packet)
        elif packet.packet_type == PacketType.ConfirmKeepAlive:
            self.packet_queque.append(packet)
        else:
            file_id = self.transfers.get(packet.file_id)
            if file_id == None:
                file_received = FileAdapter(
                    packet.file_id, False, str(packet.file_id), fragment_size=100, window_size=8)
                self.transfers[packet.file_id] = FileTransfer(
                    Direction.Receive, file_received, self.send_packet, packet)
            else:
                self.transfers[packet.file_id].add_packet(packet)

    def send_packet(self, packet: bytes):
        self.socket.sendto(packet, (self.ip, self.port))

    def send_file(self, file_name: str):
        file = FileAdapter(randint(1, 255), True, file_name,
                           fragment_size=100, window_size=8)
        self.transfers[file.id] = FileTransfer(
            Direction.Send, file, self.send_packet)
