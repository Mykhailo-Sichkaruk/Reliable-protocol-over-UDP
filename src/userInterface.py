import sys

from services import log
from MainServer import Server

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
    user_input: str = ""
    file_path: str = ""
    file_len: int = 0
    msg: str = ""
    ip: str = "0.0.0.0"
    port: int = 1000
    frame_len: int = 50
    window_size: int = 16

    while server.is_running:
        try:
            user_input = input("Enter command: ").strip()
        except KeyboardInterrupt:
            server.close()
        except EOFError:
            # set default input stdin
            sys.stdin = default_stdin

        if user_input == "exit":
            server.close()
        elif user_input.startswith("file"):
            while True:
                file_path = d_input(file_path, "Enter file path: ")
                if not check_file(file_path):
                    continue

                file = open(file_path, "rb")
                file_len = len(file.read())
                log.info(f"File size: {file_len}B")
                file.close()
                break

            ip = d_input(ip, f"Client ip ({ip}): ")
            port = int(d_input(str(port), f"Client port ({port}): "))
            while True:
                window_size = int(
                    d_input(str(window_size), f"Window size ({window_size}): "))
                frame_len = int(
                    d_input(str(frame_len), f"Frame length ({frame_len}): "))
                if check_values(window_size, frame_len, file_len):
                    break
            server.send_file(file_path, ip, port, window_size, frame_len)
        elif user_input.startswith("msg"):
            msg = input("Enter message: ")
            ip = d_input(ip, f"Client ip ({ip}): ")
            port = int(d_input(str(port), f"Client port ({port}): "))
            window_size = int(
                d_input(str(window_size), f"Window size ({window_size}): "))
            frame_len = int(
                d_input(str(frame_len), f"Frame length ({frame_len}): "))
            server.send_message(msg, ip, port, window_size, frame_len)
        elif user_input.startswith("close"):
            ip = d_input(ip, f"Client ip ({ip}): ")
            port = int(d_input(str(port), f"Client port ({port}): "))
            server.close_connection(ip, port)


def check_file(file_path: str) -> bool | str:
    try:
        with open(file_path, "rb") as f:
            f.read()
    except FileNotFoundError:
        log.error("File not found")
        return False
    except PermissionError:
        log.error("Permission denied")
        return False
    return file_path


def check_values(window_size: int, fragment_len: int, file_len: int) -> bool:
    if window_size < 1 or window_size > 248:
        log.error("Window size must be between 1 and 248")
        return False
    if fragment_len < 1 or fragment_len > 1016:
        log.error("Frame length must be between 1 and 1016")
        return False
    # Check if window size divides 8
    if window_size % 8 != 0:
        log.error("Window size must be divisible by 8")
        return False
    if window_size > fragment_len * 8:
        log.error("Window size must be less than frame length * 8")
        return False
    if (file_len / (fragment_len * window_size)) > 65535:
        log.error(
            f"Too small frame length or window size for file with size:                {file_len} B")
        log.error(
            f"With current values, max file size is: frame len * window size * 65535 = {fragment_len * window_size * 65535} B")
        return False
    return True
