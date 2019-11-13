import os
import traceback

from django_spring.config import Config


def app_default_pre_setup_hook():
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


def app_default_pre_command_hook():
    import logging

    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler):
            # Datadog formatter causes issues
            handler.formatter._fmt = "%(message)s"
        else:
            logging.getLogger().removeHandler(handler)
    logging.disable(logging.INFO)


def setup_django():
    os.environ["DJANGO_SETTINGS_MODULE"] = Config.DJANGO_SETTINGS_MODULE
    try:
        app_default_pre_setup_hook()
        import django
        import sys

        argv = sys.argv[:]
        sys.argv.append("test")
        django.setup(set_prefix=False)
        sys.argv = argv
    except:
        traceback.print_exc()
        sys.exit(Config.RESTART_EXIT_CODE)
