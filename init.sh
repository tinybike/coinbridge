#!/bin/bash
# init.sh: initial configuration for coinbridge
#
# - set up a database in postgresql using settings:
#     username: coinbridge
#     database: coinbridge
#     host: localhost
#     port: 5432
# - set environment variables
# - set up bitcoin confirmation listener (walletnotify)
#
# note: this script assumes you have bitcoind installed

trap "exit" INT

echo "Install jq"
sudo apt-get install jq -y &> /dev/null

sudo service postgresql restart

echo "Reset database:"
sudo -u postgres dropuser coinbridge &> /dev/null

echo "- Create user coinbridge"
sudo -u postgres createuser -P -D -R -S coinbridge &> /dev/null

echo " - Drop and create database coinbridge"
sudo -u postgres &> /dev/null <<'POSTGRES'
dropdb coinbridge &> /dev/null
createdb coinbridge &> /dev/null
POSTGRES

echo "Set environment variables"
echo "export BRIDGE=`pwd`" >> $HOME/.profile
echo "export PGPASSFILE=$HOME/.pgpass" >> $HOME/.profile
source $HOME/.profile

echo "Create .pgpass file"
touch $HOME/.pgpass
touch $BRIDGE/coinbridge/data/pg.cfg
echo "Enter password one more time:"
read -s pgpasswd
echo localhost:5432:coinbridge:coinbridge:$pgpasswd >> $HOME/.pgpass
echo localhost:5432:coinbridge:coinbridge:$pgpasswd >> $BRIDGE/coinbridge/data/pg.cfg
chmod 600 $HOME/.pgpass
chmod 600 $BRIDGE/coinbridge/data/pg.cfg

echo "Add walletnotify flag to bitcoin.conf"
echo "walletnotify=$BRIDGE/coinbridge/bitcoin-listen %s" >> $HOME/.bitcoin/bitcoin.conf

echo "Done."
