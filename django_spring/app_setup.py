import os
import sys
import traceback
from contextlib import contextmanager

from django_spring.config import Config


def app_default_pre_setup_hook():
    disable_dd_tracing()
    simplify_logging_handlers()


def disable_dd_tracing():
    os.environ["DATADOG_TRACE_ENABLED"] = "false"
    try:
        from ddtrace import tracer

        tracer.enabled = False
    except ImportError:
        pass
    try:
        import datadog
        import mock

        datadog.statsd.get_socket = mock.MagicMock()
    except ImportError:
        pass


def simplify_logging_handlers():
    import logging

    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler):
            # Datadog formatter causes issues
            handler.formatter._fmt = "%(message)s"
        else:
            logging.getLogger().removeHandler(handler)


@contextmanager
def wrap_env(app_env):
    """
    If app_env is "test" then make django load the test settings file
    """
    if app_env == "test":
        argv = sys.argv[:]
        sys.argv.append("test")
    yield
    if app_env == "test":
        sys.argv = argv


def setup_django(app_env):
    os.environ["DJANGO_SETTINGS_MODULE"] = Config.DJANGO_SETTINGS_MODULE
    try:
        app_default_pre_setup_hook()
        import django

        with wrap_env(app_env):
            django.setup(set_prefix=False)
    except:
        traceback.print_exc()
        sys.exit(Config.RESTART_EXIT_CODE)
