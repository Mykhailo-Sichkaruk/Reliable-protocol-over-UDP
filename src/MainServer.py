import socket
import selectors

from random import randint
from typing import Any
from connection import Conn
from packetParser import MRP
from services import MSG_SEND, log


class Server:
    def __init__(self, host: str | None = None, port: int = 0, error_rate: int = 0):
        self.connections: dict[str, Conn] = {}
        self.port = port
        self.host = host
        self.error_rate = error_rate
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, port))
        self.socket.setblocking(False)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.socket, selectors.EVENT_READ, data=None)

        log.critical(f"Server started on {self.socket.getsockname()}\n")

    def start(self):
        while True:
            try:
                events: Any = self.selector.select(timeout=0)
            except ValueError:
                events = []
            for key, _ in events:
                try:
                    data, (ip, port) = key.fileobj.recvfrom(2048)
                    # Broke packet if error rate is set
                    # if self.error_rate > 0 and randint(0, self.error_rate) == 0:
                    #     data = MRP.broke_packet(data)
                    packet = MRP.deserialize(data)
                    self.dispatch_packet(packet, ip, port)
                except IOError:
                    pass

            self.run_connections()

    def run_connections(self):
        delete_connections: list[Conn] = []
        for connection in self.connections.values():
            if not connection.run():
                delete_connections.append(connection)

        for connection in delete_connections:
            connection.close()
            del self.connections[f"{connection.destination[0]}:{connection.destination[1]}"]

    def send_file(self, file_path: str, ip: str, port: int, window_len: int = 64, frame_len: int = 500):
        if self.connections.get(f"{ip}:{port}", None) is None:
            self.connections[f"{ip}:{port}"] = Conn(
                self.socket, ip, port, window_len, frame_len)

        self.connections[f"{ip}:{port}"].send_file(
            file_path, frame_len, window_len)

    def send_message(self, msg: str, ip: str, port: int, window_len: int = 64, frame_len: int = 500):
        # Create file with message
        msg_file = open(MSG_SEND, "wb")
        msg_file.write(bytes(msg, "utf-8"))
        msg_file.close()
        self.send_file(MSG_SEND, ip, port, window_len, frame_len)

    def dispatch_packet(self, packet: MRP, ip: str, port: int):
        if self.connections.get(f"{ip}:{port}", None) is None:
            self.connections[f"{ip}:{port}"] = Conn(
                self.socket, ip, port, 16, 2)

        self.connections[f"{ip}:{port}"].add_packet(packet)

    def close(self):
        # TODO: Close all connections before closing server

        for _, connection in self.connections.items():
            connection.kill()

        log.critical(f"Server closed\n")
        self.socket.close()
        self.selector.close()
        self._is_running = False

    def close_connection(self, ip: str, port: int):
        if self.connections.get(f"{ip}:{port}", None) is not None:
            self.connections[f"{ip}:{port}"].kill()
            del self.connections[f"{ip}:{port}"]
