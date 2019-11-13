import os


class Config(object):
    APP_SOCK_FILE = "/tmp/django_spring_app_{}.sock"
    CODE_RELOADER_POLL_PERIOD = 2
    DJANGO_SETTINGS_MODULE = os.environ.get("DJANGO_SETTINGS_MODULE", "settings")
    MANAGER_SOCK_FILE = "/tmp/django_spring_manager.sock"
    RESTART_EXIT_CODE = 3
