import os
import colorlog

from threading import Thread
from userInterface import handle_commands
from MainServer import Server

if not os.path.exists("./src/save"):
    os.mkdir("./src/save")

colorlog.basicConfig(level=colorlog.DEBUG)

ip = input("Enter server ip (127.0.0.1): ") or "127.0.0.1"
port = int(input("Enter server port (1000): ") or 0) or 1000
error_rate = int(
    input("1 error will be simulated for N packets (0): ") or 0) or 0
server = Server(ip, port, error_rate)

Thread(target=handle_commands, args=(server,)).start()

try:
    server.start()
except KeyboardInterrupt:
    server.close()
