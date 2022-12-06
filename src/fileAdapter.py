from packetParser import MRP


class FileAdapter:
    def __init__(self, id, send: bool, file_name, fragment_size, window_size=8):
        self.id = id
        self.send = send
        self.file_name = file_name
        self.window_size = window_size
        self.base = 0
        self.fragment_size = fragment_size
        self.file = open(file_name, "rb" if send else "wb")

    def get_next_window(self):
        if self.send:
            window: list[bytes] = []
            for _i in range(self.window_size):
                window.append(self.file.read(self.fragment_size))

            return window

    def put_next_window(self, window: list[MRP]):
        if not self.send:
            for fragment in window:
                self.file.write(fragment.payload)
