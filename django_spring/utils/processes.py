import os
import signal
from contextlib import contextmanager


@contextmanager
def sigterm_handler(sig=signal.SIGTERM):
    original_handler = signal.getsignal(sig)

    def _sigterm_handler(_sig, _frame):
        _sigterm_handler.handled = True

    _sigterm_handler.handled = False
    yield _sigterm_handler
    signal.signal(sig, original_handler)


def pid_is_alive(pid):
    try:
        os.kill(pid, 0)
        os.waitpid(pid, os.WNOHANG)
        os.kill(pid, 0)
    except OSError:
        return False
    return True
