import logging
from threading import Thread
from userInterface import handle_commands
from MainServer import Server

logging.basicConfig(level=logging.DEBUG)

server = Server()

Thread(target=handle_commands, args=(server,)).start()
server.start()
