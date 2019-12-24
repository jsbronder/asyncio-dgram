#!/usr/bin/env python

import pathlib
import setuptools
import sys

topdir = pathlib.Path(__file__).parent


def readfile(f):
    return (topdir / f).read_text("utf-8").strip()


extra_options = {}

if sys.version_info.major == 3 and sys.version_info.minor >= 7:
    extra_options["long_description_content_type"] = "text/markdown"

setuptools.setup(
    name="asyncio-dgram",
    version="1.0.0",
    description="Higher level Datagram support for Asyncio",
    long_description=readfile("README.md"),
    url="https://github.com/jsbronder/asyncio-dgram",
    author="Justin Bronder",
    author_email="jsbronder@cold-front.org",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Framework :: AsyncIO",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    packages=["asyncio_dgram"],
    python_requires=">=3.6",
    install_requires=readfile("requirements.txt").split(),
    extras_require={"test": readfile("requirements-test.txt").split()},
    **extra_options,
)
