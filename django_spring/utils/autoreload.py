import logging
import os
import time
import threading

from django_spring.config import Config
from django_spring.utils.logger import get_logger
from django_spring.app_setup import setup_django


def _run_django_code_changed_reloader():
    from django.utils.autoreload import code_changed, FILE_MODIFIED

    while True:
        change = code_changed()
        if change == FILE_MODIFIED:
            return True
        else:
            time.sleep(Config.CODE_RELOADER_POLL_PERIOD)


def _run_django_stats_reloader():
    from django.utils.autoreload import StatReloader

    class StatReloaderWithQueuedRestart(StatReloader):
        def notify_file_changed(self, path):
            self.stop()

    StatReloaderWithQueuedRestart().run_loop()
    return True


def _run_reloader(restart_queued):
    log = get_logger("[CODE_WATCHER]")
    try:
        # Django >= 2.2
        should_reload = _run_django_stats_reloader()
    except ImportError:
        should_reload = _run_django_code_changed_reloader()
    if should_reload:
        log("Restart Queued", logging.WARN)
        restart_queued.set()


def reloader_thread(restart_queued, app_env):
    setup_django(app_env)
    _run_reloader(restart_queued)


def python_reloader(main_func, restart_queued, app_env, *args, **kwargs):
    try:
        threading.Thread(target=reloader_thread, args=[restart_queued, app_env]).start()
        main_func(*args, **kwargs)
    except KeyboardInterrupt:
        pass
    if restart_queued.is_set():
        os._exit(Config.RESTART_EXIT_CODE)
