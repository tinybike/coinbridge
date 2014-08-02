## Bitcoin/PostgreSQL bridge

### Installation (Ubuntu 12.04 LTS)

    $ pip install -r requirements.txt
    $ python setup.py install

Install `bitcoind` from the bitcoin PPA (other coins need to be compiled from source):

    $ apt-get install python-software-properties -y
    $ add-apt-repository ppa:bitcoin/bitcoin -y
    $ apt-get update
    $ apt-get install bitcoind -y

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
    $ echo "walletnotify=$BRIDGE/bridge/bitcoin-notify %s" >> ~/.bitcoin/bitcoin.conf
