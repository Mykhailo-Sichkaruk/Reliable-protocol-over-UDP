import sys
import colorlog

from MainServer import Server
from services import formatter

handler = colorlog.StreamHandler()
handler.setFormatter(formatter)
log = colorlog.getLogger(__name__)
log.addHandler(handler)

# is windows
if sys.platform.startswith("win"):
    default_stdin = open("CONIN$", "r")
else:
    default_stdin = open("/dev/tty", "r")

def d_input(default: str, msg: str) -> str:
    user_input = input(msg)
    if user_input == "":
        return default
    return user_input


def handle_commands(server: Server):
    user_input: str
    file_path: str = ""
    msg: str = ""
    ip: str = "127.0.0.1"
    port: int = 1000
    frame_len: int = 50
    window_size: int = 16

    while server.is_running:
        try:
            user_input = input("Enter command: ").strip()
        except KeyboardInterrupt:
            log.info("Client stopped by user")
            server.close()
        except EOFError:
            # set default input stdin
            sys.stdin = default_stdin
        
        if user_input == "exit":
            log.info("Client stopped by user")
            server.close()
        elif user_input == "help":
            log.info("Available commands:")
            log.info("help - show this message")
            log.info("exit - exit the program")
            log.info("file")
        elif user_input.startswith("file"):
            file_path = d_input(file_path, "Enter file path: ")
            ip = d_input(ip, f"Client ip ({ip}): ")
            port = int(d_input(str(port), f"Client port (default: {port}): "))
            window_size = int(
                d_input(str(window_size), f"Window size (default: {window_size}): "))
            frame_len = int(
                d_input(str(frame_len), f"Frame length (default: {frame_len}): "))
            server.send_file(file_path, ip, port, window_size, frame_len)
        elif user_input.startswith("msg"):
            msg = input("Enter message: ")
            ip = d_input(ip, f"Client ip ({ip}): ")
            port = int(d_input(str(port), f"Client port (default: {port}): "))
            window_size = int(
                d_input(str(window_size), f"Window size (default: {window_size}): "))
            frame_len = int(
                d_input(str(frame_len), f"Frame length (default: {frame_len}): "))
            server.send_message(msg, ip, port, window_size, frame_len)
    

