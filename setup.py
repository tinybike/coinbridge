#!/usr/bin/env python
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="Coinbridge",
    version="0.1",
    description="Bitcoin/PostgreSQL bridge",
    author="Jack Peterson",
    author_email="<jack@dyffy.com>",
    maintainer="Jack Peterson",
    maintainer_email="<jack@dyffy.com>",
    url="https://github.com/tensorjack/coinbridge",
    packages=["coinbridge"],
    package_data={"coinbridge": ["./data/*.json", "./bitcoin-listen"]},
    install_requires=["sqlalchemy", "psycopg2", "bunch", "python-jsonrpc"]
    )
