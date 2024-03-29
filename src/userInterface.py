import os
import sys

from services import log
from MainServer import Server
from packetParser import MAX_WINDOW_NUMBER

MAX_WINDOW_LEN = 248
MAX_FRAME_LEN = 2040

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
    # Exit if user press CTRL-C

    user_input: str = ""
    file_path: str = "./src/save/big.exe"
    file_len: int = 0
    msg: str = ""
    ip: str = "127.0.0.1"
    port: int = 1000
    frame_len: int = 50
    window_size: int = 16

    while True:
        try:
            user_input = input("Enter command: ").strip()
        except KeyboardInterrupt:
            server.close()
        except EOFError:
            # set default input stdin
            sys.stdin = default_stdin

        if user_input == "exit":
            server.close()
            break
        elif user_input.startswith("file"):
            while True:
                file_path = d_input(
                    file_path, f"Enter file path ({file_path}): ")
                if not check_file(file_path):
                    continue

                file = open(file_path, "rb")
                file_len = os.path.getsize(file_path)
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
            window_size = 16
            frame_len = 50
            server.send_message(msg, ip, port, window_size, frame_len)
        elif user_input.startswith("close"):
            ip = d_input(ip, f"Client ip ({ip}): ")
            port = int(d_input(str(port), f"Client port ({port}): "))
            server.close_connection(ip, port)
        elif user_input.startswith("help"):
            print("Commands:")
            print("file - send file")
            print("msg - send message")
            print("close - close connection")
        else:
            log.error("Unknown command")


def check_file(file_path: str) -> bool | str:
    try:
        with open(file_path, "rb") as f:
            f.read(1)
    except FileNotFoundError:
        log.error("File not found")
        return False
    except PermissionError:
        log.error("Permission denied")
        return False
    return file_path


def check_values(window_size: int, fragment_len: int, file_len: int) -> bool:
    if window_size < 1 or window_size > MAX_WINDOW_LEN:
        log.error("Window size must be between 1 and 248")
        return False
    if fragment_len < 1 or fragment_len > MAX_FRAME_LEN:
        log.error(f"Frame length must be between 1 and {MAX_FRAME_LEN}")
        return False
    # Check if window size divides 8
    if window_size % 8 != 0:
        log.error("Window size must be divisible by 8")
        return False
    if window_size > fragment_len * 8:
        log.error("Window size must be less than frame length * 8")
        return False
    if (file_len / (fragment_len * window_size)) > MAX_WINDOW_NUMBER:
        log.error(
            f"Too small frame length or window size for file with size:                {file_len} B\n")
        log.error(
            f"With current values, max file size is: frame len * window size * {MAX_WINDOW_NUMBER} = {fragment_len * window_size * 65535} B\n")
        return False
    return True
