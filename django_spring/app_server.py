import logging
import os
import select
import signal
import sys
import time
import traceback

from django_spring.app_setup import setup_django
from django_spring.utils.autoreload import python_reloader
from django_spring.utils.logger import colour, get_logger
from django_spring.utils.processes import pid_is_alive, sigterm_handler
from django_spring.utils.socket_data import (
    bind,
    close,
    closing,
    read_json,
    fd_redirect_list,
)
from django_spring.utils.tty import FakeTTY


class AppServer(object):
    def __init__(self, restart_queued, path, app_env):
        self.app_env = app_env
        self.app_sock = None
        self.client_sock = None
        self.log = get_logger("[APP - %s]" % app_env)
        self.path = path
        self.restart_queued = restart_queued

    def run(self):
        self.log("START", logging.WARN)
        try:
            with bind(self.path) as self.app_sock:
                setup_django(self.app_env)
                self.log("READY", logging.WARN)
                self.app_sock.listen(1)

                while not self.restart_queued.is_set():
                    ins, _, _ = select.select([self.app_sock], [], [], 1)
                    if ins:
                        self.client_sock, _ = ins[0].accept()
                        with closing(self.client_sock):
                            ins, _, _ = select.select([self.client_sock], [], [])
                            data = read_json(ins[0])
                            self.command_worker(data["command"])
                        self.client_sock = None
        except KeyboardInterrupt:
            pass
        finally:
            self.log("DONE", logging.WARN)

    def command_worker(self, cmd):
        p2cr, p2cw = os.pipe()
        c2pr, c2pw = os.pipe()
        child_pid = os.fork()

        if child_pid:  # parent process
            self.log("waiting on child", logging.WARN)
            close([p2cr, c2pw])

            try:
                if self.child_wait_sigterm_handler(child_pid, p2cw, c2pr):
                    self.log("received sigterm, returning", logging.WARN)
                    return
                try:
                    pid, status = os.waitpid(child_pid, 0)
                except OSError:
                    self.log("child is gone", logging.WARN)
                    return

                exit_code = os.WEXITSTATUS(status)
                c = "GREEN" if exit_code == 0 else "RED"
                self.log(
                    colour("child returned with status %s" % exit_code, c), logging.WARN
                )
            finally:
                close([p2cw, c2pr])
        else:  # child process
            close([self.app_sock, self.client_sock, p2cw, c2pr])
            sys.stdin = os.fdopen(p2cr, "r", 1)
            if sys.version_info > (3, 0):
                # Not really sure why it can't be unbuffered
                # But the other end of the pipe receives no data after a select
                sys.stdout = sys.stderr = FakeTTY(os.fdopen(c2pw, "w", 1))
            else:
                sys.stdout = sys.stderr = FakeTTY(os.fdopen(c2pw, "wb", 0))
            # Some libraries write directly to file descriptors
            os.dup2(c2pw, 1)
            os.dup2(c2pw, 2)

            exit_code = 0
            try:
                self.log(colour("running command `%s`" % cmd, "GREEN"), logging.WARN)
                try:
                    command_execute(cmd)
                except SystemExit as e:
                    exit_code = e.code
                except KeyboardInterrupt:
                    pass
            except BaseException as e:
                exit_code = -1
                traceback.print_exc()
                self.log("command failed: %s" % e, logging.ERROR)
            finally:
                os._exit(exit_code)

    def child_wait_sigterm_handler(self, child_pid, p2cw, c2pr):
        redirect_list = {self.client_sock: p2cw, c2pr: self.client_sock}

        def _kill_child():
            self.log("killing child process", logging.WARN)
            os.kill(child_pid, signal.SIGTERM)
            time.sleep(0.2)

        with sigterm_handler() as handler:
            while pid_is_alive(child_pid):
                if handler.handled:
                    _kill_child()
                else:
                    ins, _, _ = select.select(redirect_list.keys(), [], [], 1)
                    if not fd_redirect_list(ins, redirect_list):
                        _kill_child()
            return handler.handled


def command_execute(cmd):
    from django.core import management

    sys.argv = ["spring"] + cmd.split(" ")
    return management.ManagementUtility(sys.argv).execute()


if __name__ == "__main__":
    from threading import Event

    restart_queued = Event()
    app_env = sys.argv[2]
    app_server = AppServer(
        restart_queued=restart_queued, path=sys.argv[1], app_env=app_env
    )
    python_reloader(app_server.run, restart_queued, app_env)
