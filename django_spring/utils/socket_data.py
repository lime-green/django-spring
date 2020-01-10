import functools
import json
import os
import socket
import time
from contextlib import contextmanager


@contextmanager
def bind(path):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    if os.path.exists(path):
        os.unlink(path)
    sock.bind(path)
    with closing(sock):
        yield sock
    if os.path.exists(path):
        os.unlink(path)


@contextmanager
def closing(sock):
    try:
        yield
    finally:
        try:
            # macOS seems to disconnect the socket
            # before this point, so will error out
            sock.shutdown(2)
        except:
            pass
        sock.close()


def close(socks):
    for sock in socks:
        if hasattr(sock, "close"):
            sock.close()
        else:
            os.close(sock)


def write_json(data, fd):
    if hasattr(fd, "fileno"):
        fd = fd.fileno()
    as_json = json.dumps(data)
    len_s = "%16s" % len(as_json)
    os.write(fd, len_s.encode())
    os.write(fd, as_json.encode())


def _get_read_fn(sock):
    if hasattr(sock, "read"):
        read = sock.read
    elif hasattr(sock, "recv"):
        read = sock.recv
    else:
        read = functools.partial(os.read, sock)
    return read


def read_json(sock):
    """
    Reads a JSON object from the socket:
    - 16 bytes to get the length of the JSON string
    - n bytes for the JSON string
    """
    read_fn = _get_read_fn(sock)
    data_len = int(read_fn(16).decode().strip())
    data = read_fn(data_len).decode()
    return json.loads(data)


def fd_redirect(sock_in, sock_out, read_sizes=None):
    read_size = (read_sizes or {}).get(sock_in, 1024)
    read_sock_in = _get_read_fn(sock_in)
    data = read_sock_in(read_size)
    if not data:
        return False
    if hasattr(sock_out, "fileno"):
        sock_out = sock_out.fileno()
    os.write(sock_out, data)
    return True


def fd_redirect_list(socks_in, redirect_map, read_sizes=None):
    """
    Redirects every descriptor in `socks_in` according to the `redirect_map`
    dictionary which maps from input descriptors to output descriptors

    `read_sizes` is a dictionary that can return the number of bytes to
    read for a given input descriptor

    - returns True iff every redirect succeeds on redirecting data
    ie. will return false if a descriptor is closed
    """
    is_success = True
    for sock_in in socks_in:
        is_success &= fd_redirect(sock_in, redirect_map[sock_in], read_sizes)
    return is_success


def connect(path, max_attempts=5, wait_time=0.2):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    for i in range(0, max_attempts):
        try:
            sock.connect(path)
            return sock
        except socket.error:
            if i == max_attempts - 1:
                raise
            time.sleep(wait_time)
