import os
import select
import signal
import sys
import uuid

from django_spring.config import Config
from django_spring.utils.logger import get_logger
from django_spring.utils.socket_data import (
    closing,
    connect,
    fd_redirect_list,
    write_json,
)


class Client(object):
    def __init__(self, data_path, ctl_path, app_env):
        self.log = get_logger("[CLIENT]")
        self.data_path = data_path
        self.ctl_path = ctl_path
        self.app_env = app_env
        self.client_id = str(uuid.uuid1())

    def _redirect_until_socket_breaks(self, redirect_map, ignore_sigint=False):
        read_sizes = {sys.stdin: 1}
        while True:
            try:
                ins, _, _ = select.select(redirect_map.keys(), [], [])
                if not fd_redirect_list(ins, redirect_map, read_sizes):
                    break
            except KeyboardInterrupt:
                if not ignore_sigint:
                    raise

    def run(self, cmd):
        # unbuffered STDIN
        sys.stdin = os.fdopen(sys.stdin.fileno(), "rb", 0)
        data_sock = connect(self.data_path)
        ctl_sock = connect(self.ctl_path)

        with closing(data_sock), closing(ctl_sock):
            redirect_map = {data_sock: sys.stdout, sys.stdin: data_sock}
            try:
                write_json(
                    {
                        "command": cmd,
                        "app_env": self.app_env,
                        "client_id": self.client_id,
                    },
                    data_sock,
                )
                self._redirect_until_socket_breaks(redirect_map)
            except KeyboardInterrupt:
                write_json(
                    {
                        "command_ctl": "QUIT",
                        "signal": signal.SIGINT,
                        "app_env": self.app_env,
                        "client_id": self.client_id,
                    },
                    ctl_sock,
                )
                self._redirect_until_socket_breaks(redirect_map, ignore_sigint=True)


def start_client():
    app_env = "test" if sys.argv[1] == "test" else "dev"
    client = Client(
        data_path=Config.MANAGER_SOCK_FILE,
        ctl_path=Config.MANAGER_CTL_SOCK_FILE,
        app_env=app_env,
    )
    client.run(" ".join(sys.argv[1:]))


if __name__ == "__main__":
    start_client()
