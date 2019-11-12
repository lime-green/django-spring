import logging
import os
import time
import threading

from django_spring.config import Config
from django_spring.utils.logger import get_logger
from django_spring.app_setup import setup_django


def reloader_thread(restart_queued):
    setup_django()

    from django.utils.autoreload import code_changed, FILE_MODIFIED

    log = get_logger("[CODE_WATCHER]")
    while not restart_queued.is_set():
        change = code_changed()
        if change == FILE_MODIFIED:
            log("Restart Queued", logging.WARN)
            restart_queued.set()
        else:
            time.sleep(Config.CODE_RELOADER_POLL_PERIOD)


def python_reloader(main_func, restart_queued, args, kwargs):
    try:
        threading.Thread(target=reloader_thread, args=[restart_queued]).start()
        main_func(*args, **kwargs)
    except KeyboardInterrupt:
        pass
    if restart_queued.is_set():
        os._exit(Config.RESTART_EXIT_CODE)
