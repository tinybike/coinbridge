#!/usr/bin/env python
from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup

setup(
    name="coinbridge",
    version="0.1.1",
    description="Bitcoin/PostgreSQL bridge",
    author="Jack Peterson",
    author_email="<jack@dyffy.com>",
    maintainer="Jack Peterson",
    maintainer_email="<jack@dyffy.com>",
    license="MIT",
    url="https://github.com/tensorjack/coinbridge",
    download_url = 'https://github.com/tensorjack/coinbridge/tarball/0.1.1',
    packages=["coinbridge"],
    include_package_data=True,
    package_data={"coinbridge": ["./data/coins.json", "./bitcoin-listen"]},
    install_requires=["sqlalchemy", "psycopg2", "bunch", "python-jsonrpc"],
    keywords = ["bitcoin", "postgres", "transaction", "bridge"]
)
