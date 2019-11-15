import os
import select
import sys

from django_spring.config import Config
from django_spring.utils.logger import get_logger
from django_spring.utils.socket_data import (
    closing,
    connect,
    fd_redirect_list,
    write_json,
)


class Client(object):
    def __init__(self, path, app_env):
        self.log = get_logger("[CLIENT]")
        self.path = path
        self.app_env = app_env

    def run(self, cmd):
        # unbuffered STDIN
        sys.stdin = os.fdopen(sys.stdin.fileno(), "rb", 0)
        sock = connect(self.path)

        try:
            with closing(sock):
                write_json({"command": cmd, "app_env": self.app_env}, sock)
                redirect_map = {sock: sys.stdout, sys.stdin: sock}
                read_sizes = {sys.stdin: 1}
                while True:
                    ins, _, _ = select.select(redirect_map.keys(), [], [])
                    if not fd_redirect_list(ins, redirect_map, read_sizes):
                        break
        except KeyboardInterrupt:
            pass


def start_client():
    app_env = "test" if sys.argv[1] == "test" else "dev"
    client = Client(path=Config.MANAGER_SOCK_FILE, app_env=app_env)
    client.run(" ".join(sys.argv[1:]))


if __name__ == "__main__":
    start_client()
