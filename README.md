## Bitcoin/PostgreSQL bridge

### Installation (Ubuntu 12.04 LTS)

    $ pip install -r requirements.txt
    $ python setup.py install

Install `bitcoind` from the bitcoin PPA (other coins need to be compiled from source):

    $ apt-get install python-software-properties -y
    $ add-apt-repository ppa:bitcoin/bitcoin -y
    $ apt-get update
    $ apt-get install bitcoind -y

Set environment variables:
    
    $ echo "export BRIDGE=/path/to/coinbridge/bridge" >> ~/.profile
    $ source ~/.profile

Add the walletnotify flag to Bitcoin's config file:
    
    $ echo walletnotify=$BRIDGE/bitcoin-notify %s >> ~/.bitcoin/bitcoin.conf
   
Set up `pgpass` file so transaction confirmations can be autologged to Postgres:
    
    $ touch ~/.pgpass
    $ echo $PGHOST:$PGPORT:$PGUSER:$PGDATABASE:$PGPASSWORD >> ~/.pgpass
    $ chmod 600 ~/.pgpass
