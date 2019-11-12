class FakeTTY(object):
    def __init__(self, file):
        self._file = file

    def __getattr__(self, key):
        return getattr(self._file, key)

    def isatty(self):
        return True
