import logging
import multiprocessing
import os
import queue
import select
import signal
import sys
import time
import traceback

from django_spring.app_setup import setup_django
from django_spring.utils.autoreload import python_reloader
from django_spring.utils.logger import colour, get_logger
from django_spring.utils.processes import pid_is_alive, signal_handler
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
        self.log = get_logger("[APP - %s]" % app_env)
        self.path = path
        self.restart_queued = restart_queued
        self.command_worker_ctls = {}

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
                        client_sock, _ = ins[0].accept()
                        ins, _, _ = select.select([client_sock], [], [])
                        data = read_json(ins[0])
                        self._handle_data(data, client_sock)
        except KeyboardInterrupt:
            pass
        finally:
            self.log("DONE", logging.WARN)

    def _handle_data(self, data, client_sock):
        if "command" in data:
            ctl_queue = self.command_worker_ctls[
                data["client_id"]
            ] = multiprocessing.Manager().Queue()
            p = multiprocessing.Process(
                target=self.command_worker,
                args=(data["command"], client_sock, ctl_queue),
            )
            p.start()
        elif "command_ctl" in data:
            ctl_queue = self.command_worker_ctls[data["client_id"]]
            ctl_queue.put(data)

    def _command_worker_target(self, cmd, p2cr, c2pw):
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
        os.setsid()

        exit_code = 0
        try:
            self.log(colour("running command `%s`" % cmd, "GREEN"), logging.WARN)
            try:
                command_execute(cmd)
            except KeyboardInterrupt:
                pass
            except SystemExit as e:
                exit_code = e.code
        except BaseException as e:
            exit_code = -1
            traceback.print_exc()
            self.log("command failed: %s" % e, logging.ERROR)
        finally:
            os._exit(exit_code)

    def command_worker(self, cmd, client_sock, ctl_queue):
        with closing(client_sock):
            p2cr, p2cw = os.pipe()
            c2pr, c2pw = os.pipe()
            child = multiprocessing.Process(
                target=self._command_worker_target,
                kwargs=dict(cmd=cmd, p2cr=p2cr, c2pw=c2pw),
            )
            child.start()

            self.log("waiting on child", logging.WARN)
            close([p2cr, c2pw])

            try:
                if self.child_wait_sigterm_handler(
                    client_sock, child.pid, ctl_queue, p2cw, c2pr
                ):
                    self.log("child is gone, returning", logging.WARN)
                    return
                try:
                    pid, status = os.waitpid(child.pid, 0)
                except OSError:
                    self.log("child is gone", logging.WARN)
                    return

                exit_code = os.WEXITSTATUS(status)
                c = "GREEN" if exit_code == 0 else "RED"
                self.log(
                    colour("child returned with status %s" % exit_code, c), logging.WARN
                )
            finally:
                self.log("EXITING PARENT command_worker PROCESS")
                close([p2cw, c2pr])

    def child_wait_sigterm_handler(self, client_sock, child_pid, ctl_queue, p2cw, c2pr):
        redirect_list = {client_sock: p2cw, c2pr: client_sock}

        def _kill_child(sig):
            self.log("killing child process with sig %s" % sig, logging.WARN)
            # This is hacky, but nose ignores the first one
            # We can fix this pretty easily if this causes issues
            os.killpg(child_pid, sig)
            time.sleep(1)
            os.killpg(child_pid, sig)

            while pid_is_alive(child_pid):
                ins, _, _ = select.select(redirect_list.keys(), [], [], 1)
                if ins:
                    if not fd_redirect_list(ins, redirect_list):
                        break

        def _check_ctl():
            try:
                ctl_data = ctl_queue.get_nowait()
                if ctl_data["command_ctl"] == "QUIT":
                    self.log("got control data: %s" % ctl_data)
                    _kill_child(ctl_data["signal"])
                    return ctl_data["signal"]
            except queue.Empty:
                return False

        with signal_handler(signal.SIGTERM) as handler:
            while pid_is_alive(child_pid):
                check_ctl_ret = _check_ctl()
                if check_ctl_ret:
                    return check_ctl_ret

                if handler.handled:
                    _kill_child(handler.handled)
                    return handler.handled
                else:
                    ins, _, _ = select.select(redirect_list.keys(), [], [], 1)
                    if not ins:
                        continue
                    if not fd_redirect_list(ins, redirect_list):
                        continue


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
