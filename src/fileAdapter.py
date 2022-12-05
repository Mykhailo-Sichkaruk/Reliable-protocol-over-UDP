class FileAdapter:
    def __init__(self, id, send: bool, file_name, file_size, fragment_size, window_size=8):
        self.id = id
        self.send = send
        self.file_name = file_name
        self.file_size = file_size
        self.window_size = window_size
        self.base = 0
        self.fragment_size = fragment_size

        if (send):
            self.file = open(file_name, "rb")
        else:
            self.file = open(file_name, "wb")

    def get_next_window(self):
        if (self.send):
            window = []
            for i in range(self.window_size):
                window.append(self.file.read(self.fragment_size))

            return window

    def put_next_window(self, window):
        if (not self.send):
            for fragment in window:
                self.file.write(fragment)
