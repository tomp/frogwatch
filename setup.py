#!/usr/bin/env python3
from pathlib import Path
from setuptools import setup

from frogwatch.version import __version__


DESCRIPTION = "Retrieve Frogwatch data from Fieldscope for local analysis"

LONG_DESCRIPTION = """
This program queries the Fieldscope API to retrieve data about Frogwatch
observations from South Mountain Reservation.

The downloaded data is stored in local databases that make it easier to
visualize and ask questions about the observations.
"""

def read_text(filename):
    return Path(filename).read_text()

def read_reqs(filename):
    """Read a requirements file, and return the list of required modules.
    Lines that don't specify a module to install are stripped.
    """
    lines = [line.strip() for line in Path(filename).read_text().splitlines()]
    return [line for line in lines if line and not line.startswith("-")]


config = dict(
    name="frogwatch",
    version=__version__,
    description=DESCRIPTION,
    long_description=read_text("README.md"),
    author="Tom Pollard",
    author_email="pollard@alum.mit.edu",
    license="MIT",
    packages=["frogwatch"],
    tests_require=read_reqs("requirements_dev.txt"),
    extras_require={"test": ["pytest"]},
    entry_points={
        "console_scripts": [
            "frogwatch = frogwatch.frogwatch:main",
        ]
    }
)
setup(**config)
