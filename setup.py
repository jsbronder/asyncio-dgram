#!/usr/bin/env python

import pathlib
import setuptools

topdir = pathlib.Path(__file__).parent


def readfile(f):
    return (topdir / f).read_text("utf-8").strip()


setuptools.setup(
    name="asyncio-dgram",
    version="0.0.1",
    description="Higher level Datagram support for Asyncio",
    long_description=readfile("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/jsbronder/asynio-dgram",
    author="Justin Bronder",
    author_email="jsbronder@cold-front.org",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Framework :: AsyncIO",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["asyncio_dgram"],
    python_requires=">=3.7",
    install_requires=readfile("requirements.txt").split(),
    extras_require={"test": readfile("requirements-test.txt").split()},
)
