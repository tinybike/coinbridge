## CoinBridge: a Bitcoin/PostgreSQL bridge

### Installation (Ubuntu 12.04 LTS)

    $ python setup.py install

Install `bitcoind` (other coins need to be compiled from source)

    $ apt-get install python-software-properties -y
    $ add-apt-repository ppa:bitcoin/bitcoin -y
    $ apt-get update
    $ apt-get install bitcoind -y

Set environment variables:
    
    $ echo "export BRIDGE=/home/jack/src/babbage/bridge" >> ~/.profile
    $ echo "export BITCOIN_RPC_USER=your_rpc_username" >> ~/.profile
    $ echo "export BITCOIN_RPC_PASS=your_rpc_password" >> ~/.profile
    $ echo "export BITCOIN_RPC_PORT=your_rpc_port" >> ~/.profile
    $ echo "export PGUSER=your_postgres_username" >> ~/.profile
    $ echo "export PGDATABASE=your_postgres_database" >> ~/.profile
    $ echo "export PGHOST=your_postgres_host" >> ~/.profile
    $ echo "export PGPORT=your_postgres_port" >> ~/.profile
    $ echo "export PGPASS=your_postgres_password" >> ~/.profile

Reload environment variables -- restart (better), or use `source ~/.profile` to update in the current shell.  Next, set up Bitcoin's config file:
    
    $ mkdir ~/.bitcoin/
    $ touch ~/.bitcoin/bitcoin.conf
    $ echo listen=1 >> ~/.bitcoin/bitcoin.conf
    $ echo server=1 >> ~/.bitcoin/bitcoin.conf
    $ echo daemon=1 >> ~/.bitcoin/bitcoin.conf
    $ echo gen=0 >> ~/.bitcoin/bitcoin.conf
    $ echo testnet=0 >> ~/.bitcoin/bitcoin.conf
    $ echo rpcallowip=127.0.0.1 >> ~/.bitcoin/bitcoin.conf
    $ echo rpcuser=YOUR_RPC_USERNAME >> ~/.bitcoin/bitcoin.conf
    $ echo rpcpassword=YOUR_RPC_PASSWORD >> ~/.bitcoin/bitcoin.conf
    $ echo walletnotify=$BRIDGE/bitcoin-notify %s >> ~/.bitcoin/bitcoin.conf

    $ chmod a+x $BRIDGE/bitcoin-notify

Install PostgreSQL and create a user, database, and transactions table:

    $ apt-get install postgresql postgresql-contrib -y
    $ sudo -i -u postgres
    $ psql -c "CREATE DATABASE $PGDATABASE ENCODING 'SQL_ASCII' TEMPLATE=template0;"
    $ psql -c "CREATE USER $PGUSER WITH PASSWORD '$PGPASS';"
    $ psql -c "GRANT ALL PRIVILEGES ON DATABASE '$PGDATABASE' TO $PGUSER;"
    $ logout
    $ psql -U$PGUSER -h$PGHOST -d$PGDATABASE -c "CREATE TABLE transactions (id SERIAL PRIMARY KEY, user_id INTEGER, txhash VARCHAR(100), txdate TIMESTAMP DEFAULT transaction_timestamp(), amount DECIMAL(24,8), currency VARCHAR(25), coin_address VARCHAR(100), inbound BOOLEAN, confirmations INTEGER DEFAULT 0, last_confirmation TIMESTAMP);"

Set up `pgpass` file so transaction confirmations can be autologged to postgres:
    
    $ touch ~/.pgpass
    $ echo $PGHOST:$PGPORT:$PGUSER:$PGDATABASE:$PGPASSWORD >> ~/.pgpass
    $ chmod 600 ~/.pgpass

Set up the transaction table:
    
    $ python $BRIDGE/models.py

Run `bitcoind` (and wait for the blockchain to download):
    
    $ bitcoind
