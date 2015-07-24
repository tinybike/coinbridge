Bitcoin/PostgreSQL bridge
-------------------------

.. image:: https://travis-ci.org/tinybike/coinbridge.svg?branch=master
    :target: https://travis-ci.org/tinybike/coinbridge

.. image:: https://badge.fury.io/py/coinbridge.svg
    :target: http://badge.fury.io/py/coinbridge

Bridge between Bitcoin and PostgreSQL.

Coinbridge connects the Bitcoin daemon (bitcoind) and a local PostgreSQL
database. It listens for transaction confirmations and automatically
updates a transactions table in your database.

Includes a "payment" method which uses free, instant Bitcoin transfers
between accounts in the same wallet, and standard Bitcoin transactions
otherwise. Also includes a comprehensive wrapper for
Bitcoin's JSON-RPC functionality.

Coinbridge has been tested with Bitcoin, but it should work for any
altcoin that shares Bitcoin's RPC command suite (i.e., most of them). To
add a different coin, enter the new coin's information into
``coinbridge/data/coins.json``. For wallet listener functionality, you
also need to create a ``coinbridge/newcoin-listen`` script with
``newcoin-cli`` (or ``newcoind``) in place of ``bitcoin-cli``, and point
the new coin's ``walletnotify`` to this script in newcoin's configuration
file.

Bitcoin: 1CjevDn76Yg5TsEZLkbKy2A6g5hYPE3gAG

Installation
~~~~~~~~~~~~

::

    $ pip install coinbridge

Depending on your system, compiling Bitcoin from scratch can be a
headache. On Ubuntu, you can simply install ``bitcoind`` from the
bitcoin PPA:

::

    $ apt-get install python-software-properties
    $ add-apt-repository ppa:bitcoin/bitcoin
    $ apt-get update
    $ apt-get install bitcoind

A convenience script, ``init.sh``, is included that will do some initial
configuration for you. I have only tested this on Ubuntu 12.04/14.04 so
far. The below steps are only necessary if ``init.sh`` does not work for
you:

1. Set up a ``pgpass`` file so transaction confirmations can be
   autologged to Postgres. Replace HOST, PORT, USER, DATABASE, PASSWORD
   with your own settings. Note: ``coinbridge/db.py`` expects the
   username to be ``coinbridge``. If you use a different username, you
   must also create a ``coinbridge/data/pg.cfg`` file (containing the
   ``HOST:PORT:USER:DATABASE:PASSWORD`` string) so that Python can
   connect to Postgres.

   ::

       $ touch ~/.pgpass
       $ echo HOST:PORT:USER:DATABASE:PASSWORD >> ~/.pgpass
       $ chmod 600 ~/.pgpass

2. Set environment variables:

   ::

       $ echo "export BRIDGE=/path/to/coinbridge" >> ~/.profile
       $ echo "export PGPASSFILE=$HOME/.pgpass" >> ~/.profile
       $ source ~/.profile

3. Finally, you need to point Bitcoin's ``walletnotify`` at
   ``coinbridge/bitcoin-listen``:

   ::

       $ apt-get install jq
       $ echo "walletnotify=$BRIDGE/coinbridge/bitcoin-listen %s" >> ~/.bitcoin/bitcoin.conf

Usage
~~~~~

.. code-block:: python

    from coinbridge import Bridge

    bridge = Bridge()
    bridge.payment(from_account, to_account, amount)

.. |Build Status| image:: https://travis-ci.org/tinybike/coinbridge.svg
   :target: https://travis-ci.org/tinybike/coinbridge
.. |PyPI version| image:: https://badge.fury.io/py/coinbridge.svg
   :target: http://badge.fury.io/py/coinbridge
