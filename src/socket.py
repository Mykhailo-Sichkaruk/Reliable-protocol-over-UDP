from connection import Connection
from connection import Conn
from packetParser import parse_packet, MRP
import socket
import socket
import selectors

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)


class Server:
    def __init__(self, host=None, port: int = 0):
        self.connections: dict[str, Conn] = {}
        self.port = port
        self.host = host
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("localhost", self.port))
        self.socket.setblocking(False)
        print(f"Server started on {self.socket.getsockname()}")
        self.create_selector()

    def create_selector(self):
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.socket, selectors.EVENT_READ, data=None)

    def start(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                try:
                    data, (ip, port) = key.fileobj.recvfrom(1500)
                    self.dispatch_packet(parse_packet(data), ip, port)
                except Exception as e:
                    print(e)

            for connection in self.connections.values():
                connection.run()

    def send_file(self, file_name: str, ip: str, port: int, window_len: int = 32, frame_len: int = 200):
        self.connections[f"{ip}:{port}"] = Conn(
            self.socket, ip, port, window_len, frame_len)
        print(f"conn {ip}:{port} created")
        self.connections[f"{ip}:{port}"].send_file(file_name)

    def dispatch_packet(self, packet: MRP, ip: str, port: int):
        if self.connections.get(f"{ip}:{port}", None) == None:
            print(f"conn {ip}:{port} created")
            self.connections[f"{ip}:{port}"] = Conn(
                self.socket, ip, port, 32, 200)
            self.connections[f"{ip}:{port}"].add_packet(packet)
        else:
            self.connections[f"{ip}:{port}"].add_packet(packet)
