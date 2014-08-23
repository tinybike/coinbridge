## Bitcoin/PostgreSQL bridge

[![Build Status](https://travis-ci.org/tensorjack/CoinBridge.svg)](https://travis-ci.org/tensorjack/CoinBridge)

### Installation (Ubuntu 12.04 LTS)

    $ pip install -r requirements.txt
    $ python setup.py install

Depending on your system, compiling Bitcoin from scratch can be a headache.  On Ubuntu, I recommend simply installing `bitcoind` from the bitcoin PPA:

    $ apt-get install python-software-properties
    $ add-apt-repository ppa:bitcoin/bitcoin
    $ apt-get update
    $ apt-get install bitcoind

Set up `pgpass` file so transaction confirmations can be autologged to Postgres (replace HOST, PORT, USER, DATABASE, PASSWORD with your own settings):
    
    $ touch ~/.pgpass
    $ echo HOST:PORT:USER:DATABASE:PASSWORD >> ~/.pgpass
    $ chmod 600 ~/.pgpass

Set environment variables:

    $ echo "export BRIDGE=/path/to/coinbridge" >> ~/.profile
    $ echo "export PGPASSFILE=$HOME/.pgpass" >> ~/.profile
    $ source ~/.profile

Add walletnotify to Bitcoin's config file (`jq` used for shell transaction parsing):

    $ apt-get install jq
    $ echo "walletnotify=$BRIDGE/bitcoin-notify %s" >> ~/.bitcoin/bitcoin.conf
