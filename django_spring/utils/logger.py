import logging

LOG_LEVEL = logging.WARN
TERM_COLORS = {
    "RESET": "\x1b[0m",
    "RED": "\x1b[1;31m",
    "GREEN": "\x1b[1;32m",
    "YELLOW": "\x1b[1;33m",
}


def colour(msg, c):
    return "%s%s%s" % (TERM_COLORS[c], msg, TERM_COLORS["RESET"])


def _log(msg, level=logging.INFO):
    if level >= LOG_LEVEL:
        print(msg)


def get_logger(prefix, c="YELLOW"):
    def wrapper(msg, *args, **kwargs):
        msg = "%s %s" % (colour(prefix, c), msg)
        return _log(msg, *args, **kwargs)

    return wrapper
