import shutil
from socket import Server


def get_file_to_send():
    # read file name from user
    filename = input("Enter file name to send: ")
    # copy file to send to a new file
    shutil.copy(filename, filename.split(".")[
                0] + "_copy." + filename.split(".")[1])
    # return the new file name
    return filename.split(".")[0] + "_copy." + filename.split(".")[1]


def get_client_to_connect():
    ip = input("Enter client ip: ")
    port = int(input("Enter client port: "))

    return (ip, port)


def get_server_credentials():
    ip = input("Enter server ip: ")
    port = int(input("Enter server port: "))

    return (ip, port)


def main():
    try:
        file_name = "test.txt"
        server_ip, server_port = "localhost", 9999
        server = Server(server_ip, server_port)
        ip, port = "127.0.0.1", 1000
        server.send_file(file_name, ip, port)
        server.start()
    except KeyboardInterrupt:
        print("Server stopped by user")
        exit()


main()
