
class InMemoryFile:
    def __init__(self, name, mime_type, mem_link):
        self._name = name
        self._mime_type = mime_type
        self._mem_link = mem_link

    @property
    def name(self):
        return self._name

    @property
    def mime_type(self):
        return self._mime_type

    def read(self):
        return bytes(self._mem_link)
