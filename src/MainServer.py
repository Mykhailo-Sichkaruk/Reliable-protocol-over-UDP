
import logging
import socket
import selectors

from random import randint
from typing import Any
from connection import Conn
from packetParser import parse_packet, MRP
from services import MSG_SEND

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)


log = logging.getLogger("server")


class Server:
    def __init__(self, host: str | None = None, port: int = 0, error_rate: int = 0):
        self.connections: dict[str, Conn] = {}
        self.port = port
        self.host = host
        self.error_rate = error_rate
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
        self.socket.setblocking(False)
        self.create_selector()

        log.info(f"!Server started on {self.socket.getsockname()}")

    def create_selector(self):
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.socket, selectors.EVENT_READ, data=None)

    def start(self):
        while True:
            events: Any = self.selector.select(timeout=0)
            for key, mask in events:
                try:
                    data, (ip, port) = key.fileobj.recvfrom(1024)
                    # Broke packet with 0.01% probability
                    if self.error_rate > 0 and randint(0, self.error_rate) == 0:
                        log.info(f"!Broke packet from {ip}:{port}")
                        data = self.broke_packet(data)
                    self.dispatch_packet(parse_packet(data), ip, port)
                except Exception:
                    pass

            delete_connections = []
            for connection in self.connections.values():
                if not connection.run():
                    delete_connections.append(connection)

            # for connection in delete_connections:
            #     del self.connections[f"{connection.destination[0]}:{connection.destination[1]}"]

    def broke_packet(self, data: bytes):
        # Change any byte in the packet
        random_index = randint(0, len(data) - 1)
        bytearray_data = bytearray(data)
        bytearray_data[random_index] = randint(0, 255)

        return bytes(bytearray_data)

    def send_file(self, file_path: str, ip: str, port: int, window_len: int = 64, frame_len: int = 500):
        if self.connections.get(f"{ip}:{port}", None) == None:
            self.connections[f"{ip}:{port}"] = Conn(
                self.socket, ip, port, window_len, frame_len)

        self.connections[f"{ip}:{port}"].send_file(
            file_path, frame_len, window_len)

    def send_message(self, msg: str, ip: str, port: int, window_len: int = 64, frame_len: int = 500):
        # Create file with message
        msg_file = open(MSG_SEND, "w")
        msg_file.write(msg)
        msg_file.close()
        self.send_file(MSG_SEND, ip, port, window_len, frame_len)

    def dispatch_packet(self, packet: MRP, ip: str, port: int):
        if self.connections.get(f"{ip}:{port}", None) == None:
            self.connections[f"{ip}:{port}"] = Conn(
                self.socket, ip, port, 16, 2)
            self.connections[f"{ip}:{port}"].add_packet(packet)
        else:
            self.connections[f"{ip}:{port}"].add_packet(packet)
