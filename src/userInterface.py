import logging
from MainServer import Server

log = logging.getLogger(__name__)


def handle_commands(server: Server):
    user_input: str

    while True:
        try:
            user_input = input("Enter command: ").strip()
        except KeyboardInterrupt:
            log.info("Client stopped by user")
            exit()

        if user_input == "exit":
            log.info("Client stopped by user")
            exit()
        elif user_input == "help":
            log.info("Available commands:")
            log.info("help - show this message")
            log.info("exit - exit the program")
            log.info("file")
        elif user_input.startswith("file"):
            file_path = input("Enter file path: ")
            ip, port = input("Enter client ip: "), int(input(
                "Enter client port: "))
            frame_len, window_size = int(input(
                "Enter frame length: ")), int(input("Enter window size: "))
            server.send_file(file_path, ip, port, window_size, frame_len)
