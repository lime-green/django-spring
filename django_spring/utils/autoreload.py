import logging
import os
import time
import threading

from django_spring.app_setup import setup_django
from django_spring.config import Config
from django_spring.utils.logger import get_logger
from django_spring.utils.preload import preload_views


def _run_django_code_changed_reloader(log):
    from django.utils.autoreload import (
        code_changed,
        FILE_MODIFIED,
        inotify_code_changed,
        USE_INOTIFY,
    )

    if USE_INOTIFY:
        preload_views()
        fn = inotify_code_changed
    else:
        log(
            "Using stat reloader which is CPU intensive. To fix: `pip install pyinotify`",
            logging.WARN,
        )
        fn = code_changed
    while True:
        change = fn()
        if change == FILE_MODIFIED:
            return True
        else:
            time.sleep(Config.CODE_RELOADER_POLL_PERIOD)


def _get_reloader(log):
    from django.utils.autoreload import (
        StatReloader,
        WatchmanReloader,
        WatchmanUnavailable,
    )

    try:
        WatchmanReloader.check_availability()

        class WatchmanReloaderWithQueuedRestart(WatchmanReloader):
            def notify_file_changed(self, path):
                self.stop()

        return WatchmanReloaderWithQueuedRestart()
    except WatchmanUnavailable:
        log(
            "Using stat reloader which is CPU intensive. To fix: Install Watchman and `pip install pywatchman`",
            logging.WARN,
        )

        class StatReloaderWithQueuedRestart(StatReloader):
            SLEEP_TIME = Config.CODE_RELOADER_POLL_PERIOD

            def notify_file_changed(self, path):
                self.stop()

        return StatReloaderWithQueuedRestart()


def _run_django_reloader(log):
    _get_reloader(log).run_loop()
    return True


def _run_reloader(restart_queued):
    log = get_logger("[CODE_WATCHER]")
    try:
        # Django >= 2.2
        should_reload = _run_django_reloader(log)
    except ImportError:
        should_reload = _run_django_code_changed_reloader(log)
    if should_reload:
        log("Restart Queued", logging.WARN)
        restart_queued.set()


def reloader_thread(restart_queued, app_env):
    try:
        setup_django(app_env)
        _run_reloader(restart_queued)
    except KeyboardInterrupt:
        pass


def python_reloader(main_func, restart_queued, app_env, *args, **kwargs):
    try:
        threading.Thread(target=reloader_thread, args=[restart_queued, app_env]).start()
        main_func(*args, **kwargs)
    except KeyboardInterrupt:
        pass
    if restart_queued.is_set():
        os._exit(Config.RESTART_EXIT_CODE)
