import importlib
import os
import pkgutil
from setuptools import find_packages

from django_spring.utils.logger import get_logger


log = get_logger("[PRELOAD]")
ROOT_DIR = os.getcwd()


def preload_views():
    """
    File watchers only watch files that have been loaded

    Calling `preload_all_modules` loads all the modules so that changes
    are detected properly
    """
    log("Starting `preload_views`")
    modules = set()
    for pkg in find_packages(ROOT_DIR):
        pkgpath = ROOT_DIR + "/" + pkg.replace(".", "/")
        for info in pkgutil.iter_modules([pkgpath]):
            if info.ispkg:
                continue
            if info.name != "views":
                continue
            modules.add(pkg + "." + info.name)
    for module in modules:
        try:
            importlib.import_module(module)
        except Exception as e:  # pylint: disable=broad-except
            log("{} failed to load: {}".format(module, e))
    log("Done `preload_views`")
