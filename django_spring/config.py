import os


class Config(object):
    APP_SOCK_FILE = "/tmp/django_spring_app_{}.sock"
    CODE_RELOADER_POLL_PERIOD = int(os.environ.get("CODE_RELOADER_POLL_PERIOD", 5))
    DJANGO_SETTINGS_MODULE = os.environ.get("DJANGO_SETTINGS_MODULE", "settings")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARN")
    MANAGER_SOCK_FILE = "/tmp/django_spring_manager.sock"
    MANAGER_CTL_SOCK_FILE = "/tmp/django_spring_manager_ctl.sock"
    RESTART_EXIT_CODE = 3
