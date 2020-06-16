import logging
import multiprocessing
import os
import select
import signal
import subprocess
import sys
import threading
import time


from django_spring.config import Config
from django_spring.utils.logger import get_logger
from django_spring.utils.processes import pid_is_alive
from django_spring.utils.socket_data import (
    bind,
    closing,
    connect,
    read_json,
    fd_redirect_list,
    write_json,
)


class ClientToAppControlThread(threading.Thread):
    def __init__(self, app_servers, client_sock):
        threading.Thread.__init__(self)
        self.app_servers, self.client_sock = app_servers, client_sock

    def send_msg(self, msg):
        app_sock = connect(
            self.app_servers[msg["app_env"]], wait_time=1, max_attempts=5
        )
        with closing(app_sock):
            write_json(msg, app_sock)

    def run(self):
        log = get_logger("[CLIENT_CTL_THREAD]")
        log("START")

        try:
            with closing(self.client_sock):
                ins, _, _ = select.select([self.client_sock], [], [])
                if ins:
                    try:
                        msg = read_json(ins[0])
                    except ValueError:
                        # could be empty string if client disconnects
                        return
                    self.send_msg(msg)
        finally:
            log("DONE")


class ClientToAppDataThread(threading.Thread):
    def __init__(self, app_servers, client_sock):
        threading.Thread.__init__(self)
        self.app_servers, self.client_sock = app_servers, client_sock

    def run(self):
        log = get_logger("[CLIENT_DATA_THREAD]")
        log("START")

        try:
            with closing(self.client_sock):
                ins, _, _ = select.select([self.client_sock], [], [])
                if ins:
                    msg = read_json(ins[0])
                    app_env = msg["app_env"]
                    app_sock = connect(
                        self.app_servers[app_env], wait_time=3, max_attempts=10
                    )
                    with closing(app_sock):
                        write_json(msg, app_sock)
                        redirect_map = {
                            app_sock: self.client_sock,
                            self.client_sock: app_sock,
                        }

                        while True:
                            ins, _, _ = select.select(redirect_map.keys(), [], [])
                            if not fd_redirect_list(ins, redirect_map):
                                break
        finally:
            log("DONE")


class Manager(object):
    def __init__(self, path_server, path_ctl):
        self.app_servers = multiprocessing.Manager().dict()
        self.path_server = path_server
        self.path_ctl = path_ctl
        self.log = get_logger("[MANAGER]")

    def _start_app_server(self, app_server_id):
        path = Config.APP_SOCK_FILE.format(app_server_id)
        multiprocessing.Process(
            target=self._watch, args=(app_server_id, path), daemon=True
        ).start()

    def _watch(self, app_server_id, sock_file_path):
        def _exit_child(process, exit_signal):
            if not process:
                return
            try:
                self.log("killing subprocess %s" % exit_signal)
                os.kill(process.pid, exit_signal)
            except OSError:
                pass
            while pid_is_alive(process.pid):
                time.sleep(1)

        def _poll_child(process):
            exit_code = process.poll()
            if exit_code is None:
                time.sleep(1)
                return process, False
            elif exit_code != Config.RESTART_EXIT_CODE:
                self.log("exit_code other than restart code: %s" % exit_code)
                return None, True
            else:
                return None, False

        def _spawn_child():
            self.log("starting subprocess")
            app_server_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "app_server.py"
            )
            args = (
                [sys.executable]
                + ["-W%s" % o for o in sys.warnoptions]
                + [app_server_path]
                + [sock_file_path]
                + [app_server_id]
            )
            new_environ = os.environ.copy()
            return subprocess.Popen(args, env=new_environ)

        p = None
        try:
            while True:
                if p:
                    p, err = _poll_child(p)
                    if err:
                        del self.app_servers[app_server_id]
                        return
                else:
                    p = _spawn_child()
                    self.app_servers[app_server_id] = sock_file_path
        except KeyboardInterrupt:
            pass
        finally:
            _exit_child(p, signal.SIGTERM)

    def run(self):
        try:
            with bind(self.path_server) as manager_sock, bind(
                self.path_ctl
            ) as manager_ctl:
                self._start_app_server("test")
                self._start_app_server("dev")
                manager_sock.listen(1)
                manager_ctl.listen(1)
                self.log("START LOOP", logging.WARN)

                while True:
                    ins, _, _ = select.select([manager_sock], [], [], 1)
                    if ins:
                        client_sock, _ = ins[0].accept()
                        ClientToAppDataThread(
                            app_servers=self.app_servers, client_sock=client_sock
                        ).start()
                    ins, _, _ = select.select([manager_ctl], [], [], 1)
                    if ins:
                        client_sock, _ = ins[0].accept()
                        ClientToAppControlThread(
                            app_servers=self.app_servers, client_sock=client_sock
                        ).start()
        except KeyboardInterrupt:
            pass
        finally:
            self.log("STOP LOOP", logging.WARN)


def start_manager():
    Manager(Config.MANAGER_SOCK_FILE, Config.MANAGER_CTL_SOCK_FILE).run()


if __name__ == "__main__":
    start_manager()
