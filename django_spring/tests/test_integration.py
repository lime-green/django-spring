import os
import signal
import subprocess
from contextlib import contextmanager

import django
import pytest


DJANGO_VERSION_MAJOR_MINOR = tuple(map(int, django.__version__.split('.')[:2]))
THIS_DIR = os.path.dirname(os.path.abspath(__file__))


@contextmanager
def spring_daemon(folder_name):
    os.chdir(os.path.join(THIS_DIR, folder_name))
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "{}.settings".format(folder_name)
    p = subprocess.Popen(
        "spring start",
        env=env,
        shell=True,
    )
    try:
        yield p
    finally:
        os.kill(p.pid, signal.SIGINT)
        p.wait()


def run_spring_command(cmd):
    env = os.environ.copy()
    return subprocess.Popen(
        "spring %s" % cmd,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
    )


@pytest.mark.skipif(
    DJANGO_VERSION_MAJOR_MINOR != (1, 11), reason="Requires django 1.11"
)
def test_django_1_11():
    folder_name = "django_1_11_project"
    with spring_daemon(folder_name) as p:
        s = run_spring_command("test")
        out, err = s.communicate()
        assert b"OK" in out, "STDOUT: %s, STDERR: %s" % (out, err)


@pytest.mark.skipif(
    DJANGO_VERSION_MAJOR_MINOR != (2, 2), reason="Requires django 2.2"
)
def test_django_2_2():
    folder_name = "django_2_2_project"
    with spring_daemon(folder_name) as p:
        s = run_spring_command("test")
        out, err = s.communicate()
        assert b"OK" in out, "STDOUT: %s, STDERR: %s" % (out, err)


@pytest.mark.skipif(
    DJANGO_VERSION_MAJOR_MINOR != (3, 0), reason="Requires django 3.0"
)
def test_django_3_0():
    folder_name = "django_3_0_project"
    with spring_daemon(folder_name) as p:
        s = run_spring_command("test")
        out, err = s.communicate()
        assert b"OK" in out, "STDOUT: %s, STDERR: %s" % (out, err)
