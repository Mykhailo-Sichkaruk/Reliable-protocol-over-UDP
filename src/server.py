import string
from packetParser import parse_MRP, MRP, PacketType
import socket
import socket
import selectors
import shutil

selector = selectors.DefaultSelector()

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)


def callback(sock):
    data, (ip, port) = sock.recvfrom(1024)
    print(f"{ip}:{port} -- {data}")


base_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
base_socket.bind((HOST, PORT))
print(f"Server started on {HOST}:{PORT}")
base_socket.setblocking(False)
selector.register(base_socket, selectors.EVENT_READ, data=None)


class Server:
    def __init__(self, port=None, host=None):
        self.connections = {}
        self.port = port
        self.host = host
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.host, self.port))
        self.socket.setblocking(False)
        print(f"Server started on {self.host}:{self.port}")
        self.create_selector()
        self.start()

    def create_selector(self):
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.socket, selectors.EVENT_READ, data=None)

    def start(self):
        while True:
            events = self.selector.select(timeout=None)
            for key, mask in events:
                data, (ip, port) = key.fileobj.recvfrom(1500)
                self.dispatch_packet(parse_MRP(data), ip, port)

    def dispatch_packet(self, packet: MRP, ip, port):
        if self.connections.get(f"{ip}:{port}") is None:
            self.connections[f"{ip}:{port}"] = Connection(ip, port, packet)


def get_file_to_send():
    # read file name from user
    filename = input("Enter file name to send: ")
    # copy file to send to a new file
    shutil.copy(filename, filename.split(".")[
                0] + "_copy." + filename.split(".")[1])
    # return the new file name
    return filename.split(".")[0] + "_copy." + filename.split(".")[1]


try:
    file = get_file_to_send()
    start_server(file)
except KeyboardInterrupt:
    base_socket.close()
