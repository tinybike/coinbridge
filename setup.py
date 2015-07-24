#!/usr/bin/env python
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name="coinbridge",
    version="0.1.4",
    description="Bitcoin/PostgreSQL bridge",
    author="Jack Peterson",
    author_email="<jack@tinybike.net>",
    maintainer="Jack Peterson",
    maintainer_email="<jack@tinybike.net>",
    license="MIT",
    url="https://github.com/tinybike/coinbridge",
    download_url = "https://github.com/tinybike/coinbridge/tarball/0.1.4",
    packages=["coinbridge"],
    include_package_data=True,
    package_data={"coinbridge": ["./data/coins.json", "./bitcoin-listen"]},
    install_requires=["sqlalchemy", "psycopg2", "bunch", "python-jsonrpc"],
    keywords = ["bitcoin", "postgres", "transaction", "bridge"]
)
