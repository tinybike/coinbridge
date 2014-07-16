#!/bin/bash

sudo pip install -r requirements.txt
sudo python setup.py install --record files.txt

sudo apt-get install python-software-properties -y
sudo add-apt-repository ppa:bitcoin/bitcoin -y
sudo apt-get update
sudo apt-get install bitcoind -y

echo "export BRIDGE=/path/to/coinbridge/bridge" >> ~/.profile
echo "export BITCOIN_RPC_USER=your_rpc_username" >> ~/.profile
echo "export BITCOIN_RPC_PASS=your_rpc_password" >> ~/.profile
echo "export BITCOIN_RPC_PORT=your_rpc_port" >> ~/.profile
echo "export PGUSER=your_postgres_username" >> ~/.profile
echo "export PGDATABASE=your_postgres_database" >> ~/.profile
echo "export PGHOST=your_postgres_host" >> ~/.profile
echo "export PGPORT=your_postgres_port" >> ~/.profile
echo "export PGPASS=your_postgres_password" >> ~/.profile

source ~/.profile

mkdir ~/.bitcoin/
touch ~/.bitcoin/bitcoin.conf
echo listen=1 >> ~/.bitcoin/bitcoin.conf
echo server=1 >> ~/.bitcoin/bitcoin.conf
echo daemon=1 >> ~/.bitcoin/bitcoin.conf
echo gen=0 >> ~/.bitcoin/bitcoin.conf
echo testnet=0 >> ~/.bitcoin/bitcoin.conf
echo rpcallowip=127.0.0.1 >> ~/.bitcoin/bitcoin.conf
echo rpcuser=YOUR_RPC_USERNAME >> ~/.bitcoin/bitcoin.conf
echo rpcpassword=YOUR_RPC_PASSWORD >> ~/.bitcoin/bitcoin.conf
echo walletnotify=$BRIDGE/bitcoin-notify %s >> ~/.bitcoin/bitcoin.conf

chmod a+x $BRIDGE/bitcoin-notify

apt-get install postgresql postgresql-contrib -y
sudo -i -u postgres
psql -c "CREATE DATABASE $PGDATABASE ENCODING 'SQL_ASCII' TEMPLATE=template0;"
psql -c "CREATE USER $PGUSER WITH PASSWORD '$PGPASS';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE '$PGDATABASE' TO $PGUSER;"
logout

touch ~/.pgpass
echo $PGHOST:$PGPORT:$PGUSER:$PGDATABASE:$PGPASSWORD >> ~/.pgpass
chmod 600 ~/.pgpass

bitcoind
echo "bitcoind started!"
