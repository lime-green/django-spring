import logging
import multiprocessing
import os
import select
import sys
import threading
import time


from django_spring.config import Config
from django_spring.utils.logger import get_logger
from django_spring.utils.socket_data import (
    bind,
    closing,
    connect,
    read_json,
    fd_redirect_list,
    write_json,
)


class ClientThread(threading.Thread):
    def __init__(self, app_servers, client_sock):
        threading.Thread.__init__(self)
        self.app_servers, self.client_sock = app_servers, client_sock

    def run(self):
        log = get_logger("[CLIENT_WORKER]")

        ins, _, _ = select.select([self.client_sock], [], [])
        if ins:
            msg = read_json(ins[0])
            app_env = msg["app_env"]

            app_sock = connect(self.app_servers[app_env], wait_time=3, max_attempts=10)
            with closing(app_sock), closing(self.client_sock):
                write_json(msg, app_sock)
                redirect_map = {app_sock: self.client_sock, self.client_sock: app_sock}

                while True:
                    ins, _, _ = select.select(redirect_map.keys(), [], [])
                    if not fd_redirect_list(ins, redirect_map):
                        break
            log("DONE", logging.WARN)


class Manager(object):
    def __init__(self, path):
        self.app_servers = multiprocessing.Manager().dict()
        self.path = path
        self.log = get_logger("[MANAGER]")

    def _start_app_server(self, app_server_id):
        path = Config.APP_SOCK_FILE.format(app_server_id)
        multiprocessing.Process(target=self._watch, args=[app_server_id, path]).start()

    def _watch(self, app_server_id, sock_file_path):
        import subprocess

        def _exit_child(process):
            if not process:
                return
            try:
                process.terminate()
            except OSError:
                pass

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
            _exit_child(p)

    def run(self):
        try:
            with bind(self.path) as manager_sock:
                self._start_app_server("test")
                self._start_app_server("dev")
                manager_sock.listen(1)
                self.log("START LOOP", logging.WARN)

                while True:
                    ins, _, _ = select.select([manager_sock], [], [])
                    if ins:
                        client_sock, _ = ins[0].accept()
                        ClientThread(
                            app_servers=self.app_servers, client_sock=client_sock
                        ).start()
        except KeyboardInterrupt:
            pass
        finally:
            self.log("STOP LOOP", logging.WARN)


def start_manager():
    Manager(Config.MANAGER_SOCK_FILE).run()


if __name__ == "__main__":
    start_manager()
