import os
from os.path import join, exists

from setuptools import find_packages, setup

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Natural Language :: English",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: Implementation :: CPython",
    "Topic :: Software Development :: Libraries ",
]


INSTALL_REQUIRES = []

base_dir = os.path.dirname(__file__)
readme_path = join(base_dir, "README.md")
if exists(readme_path):
    with open(readme_path) as stream:
        long_description = stream.read()
else:
    long_description = ""

setup(
    name="django-spring",
    classifiers=CLASSIFIERS,
    packages=find_packages(),
    version="0.0.5",
    description="Django App Preloader",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lime-green/django-spring",
    scripts=["django_spring/bin/spring"],
    install_requires=INSTALL_REQUIRES,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4",
)
