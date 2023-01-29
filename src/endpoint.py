import os
import services
from threading import Thread
from userInterface import handle_commands
from MainServer import Server

if not os.path.exists("./src/save"):
    os.mkdir("./src/save")

while True:
    try:
        ip = input("Enter server ip (127.0.0.1): ") or "127.0.0.1"
        port = int(input("Enter server port (1000): ") or 0) or 1000
        server = Server(ip, port, 0)
        break
    except Exception as e:
        services.log.error(e)
        continue

Thread(target=handle_commands, args=(server,)).start()

try:
    server.start()
except KeyboardInterrupt:
    server.close()
