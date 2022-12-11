import logging
import colorlog

from threading import Thread
from userInterface import handle_commands
from MainServer import Server

logging.basicConfig(level=logging.DEBUG)

ip = input("Enter server ip: ") or "127.0.0.1"
port = int(input("Enter server port: ") or 0) or 1000
server = Server(ip, port)

Thread(target=handle_commands, args=(server,)).start()
server.start()
