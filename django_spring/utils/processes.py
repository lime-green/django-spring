import os
import signal
from contextlib import contextmanager


@contextmanager
def signal_handler(*signals):
    if not signals:
        signals = [signal.SIGTERM]
    original_signals = dict()

    def _signal_handler(sig, _frame):
        _signal_handler.handled = sig

    for s in signals:
        original_signals[s] = signal.getsignal(s)
        signal.signal(s, _signal_handler)

    _signal_handler.handled = None
    yield _signal_handler

    for s, handler in original_signals.items():
        signal.signal(s, handler)


def pid_is_alive(pid):
    try:
        os.kill(pid, 0)
        os.waitpid(pid, os.WNOHANG)
        os.kill(pid, 0)
    except OSError:
        return False
    return True
