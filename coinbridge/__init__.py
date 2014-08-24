#!/usr/bin/env python
"""Bridge between Bitcoin and PostgreSQL.

Connects the Bitcoin daemon (bitcoind) and a local PostgreSQL
database. Listens for transaction confirmations and automatically
updates a transactions table in your database.

Includes a "payment" method which uses free, instant Bitcoin transfers
between accounts in the same wallet, and standard Bitcoin transactions
otherwise. Also includes a comprehensive wrapper for bitcoind/bitcoin-cli
JSON-RPC functionality.

Usage:
    from coinbridge import Bridge
    bridge = Bridge()
    bridge.payment(from_account, to_account, amount)

"""
from __future__ import division, unicode_literals
try:
    import sys
    import cdecimal
    sys.modules["decimal"] = cdecimal
except:
    pass
import os
import platform
import traceback
import urllib2
import json
import time
import logging
from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN
from contextlib import contextmanager
from functools import wraps
import pyjsonrpc
import db

__title__      = "Coinbridge"
__version__    = "0.1.1"
__author__     = "Jack Peterson"
__copyright__  = "Copyright 2014, Dyffy Inc."
__license__    = "MIT"
__maintainer__ = "Jack Peterson"
__email__      = "jack@dyffy.com"

_IS_PYTHON_3 = (platform.version() >= '3')
identity = lambda x : x
if _IS_PYTHON_3:
    u = identity
else:
    import codecs
    def u(string):
        return codecs.unicode_escape_decode(string)[0]

HERE = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(HERE, "data", "coins.json")) as coinfile:
    COINS = json.load(coinfile)

db.init()

def error_handler(task):
    """Handle and log RPC errors."""
    @wraps(task)
    def wrapper(self, *args, **kwargs):
        try:
            return task(self, *args, **kwargs)
        except Exception as e:
            self.connected = False
            if not self.testing:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                error_message = (
                    "[" + str(datetime.now()) + "] Error in task \"" +
                    task.__name__ + "\" (" +
                    fname + "/" + str(exc_tb.tb_lineno) +
                    ")" + e.message
                )
                self.logger.error("%s: RPC instruction failed" % error_message)
    return wrapper

class Bridge(object):
    """Interface and convenience functions for coin daemon interaction.

    Bridge includes "payment", a convenience method for sending Bitcoins.  Uses
    free, instant "move" transfers between accounts in the same wallet, and
    standard "sendfrom" transactions otherwise.  Useful for websites where
    many user accounts are stored in the same wallet.

    All payments are automatically logged to the 'transactions' table in your
    PostgreSQL database.

    """
    def __init__(self, coin="Bitcoin", testnet=False, reconnect=True,
                 testing=False, loglevel=logging.INFO):
        """
        Args:
          coin (str): name of the coin (default="Bitcoin")
          testnet (bool): True for the testnet, False for the mainnet (default)
          loglevel (int): logging.{DEBUG, INFO, WARN, ERROR}
          reconnect (bool): True to automatically reconnect (default)
          testing (bool): True if unit testing, False otherwise (default)

        Attributes:
          coin (str): lower-case name of the coin
          connected (bool): True if connected to the coin daemon, False otherwise
          quantum (Decimal): number of digits to include after the decimal point

        """
        logging.basicConfig(level=loglevel)
        self.logger = logging.getLogger(__name__)
        self.coin = coin.lower()
        self.connected = False
        self.quantum = Decimal("1e-"+str(COINS[self.coin]["decimals"]))
        self.testnet = testnet
        self.testing = testing
        self.reconnect = reconnect
        self.rpc_connect()

    @contextmanager
    def openwallet(self):
        self.walletunlock()
        yield
        self.walletlock()

    @error_handler
    def payment(self, origin, destination, amount):
        """Convenience method for sending Bitcoins.

        Send coins from origin to destination. Calls record_tx to log the
        transaction to database.  Uses free, instant "move" transfers
        if addresses are both local (in the same wallet), and standard
        "sendfrom" transactions otherwise.

        The sender is required to be specified by user_id (account label);
        however, the recipient can be specified either by Bitcoin address
        (anyone) or user_id (if the user is local).

        Payment tries sending Bitcoins in this order:
          1. "move" from account to account (local)
          2. "move" from account to address (local)
          3. "sendfrom" account to address (broadcast)

        Args:
          origin (str): user_id of the sender
          destination (str): coin address or user_id of the recipient
          amount (str, Decimal, number): amount to send

        Returns:
          bool: True if successful, False otherwise

        """
        if type(amount) != Decimal:
            amount = Decimal(amount)
        if amount <= 0:
            raise Exception("Amount must be a positive number")

        # Check if the destination is within the same wallet;
        # if so, we can use the fast (and free) "move" command
        all_addresses = []
        accounts = self.listaccounts()
        if origin in accounts:
            if destination in accounts:
                with self.openwallet():
                    result = self.move(origin, destination, amount)
                return self.record_tx(origin, None, amount,
                                      result, destination)
            for account in accounts:
                addresses = self.getaddressesbyaccount(account)
                if destination in addresses:
                    with self.openwallet():
                        result = self.move(origin, account, amount)
                    return self.record_tx(origin, destination, amount,
                                          result, account)

            # Didn't find anything, so use "sendfrom" instead
            else:
                with self.openwallet():
                    txhash = self.sendfrom(origin, destination, amount)
                return self.record_tx(origin, destination, amount, txhash)

    @error_handler
    def record_tx(self, origin, destination, amount,
                  outcome, destination_id=None):
        """Records a transaction in the database.

        Args:
          origin (str): user_id of the sender
          destination (str): coin address or user_id of the recipient
          amount (str, Decimal, number): amount to send
          outcome (str, bool): the transaction hash if this is a "sendfrom"
                               transaction; for "move", True if successful,
                               False otherwise
          destination_id (str): the destination account label ("move" only)

        Returns:
          str or bool: the outcome (input) argument

        """
        # "move" commands
        if destination_id:
            tx = db.Transaction(
                txtype="move",
                from_user_id=origin,
                to_user_id=destination_id,
                txdate=datetime.now(),
                amount=amount,
                currency=COINS[self.coin]["ticker"],
                to_coin_address=destination,
            )

        # "sendfrom" commands
        else:
            self.logger.debug(self.gettransaction(outcome))
            confirmations = self.gettransaction(outcome)["confirmations"]
            last_confirmation = datetime.now() if confirmations else None
            tx = db.Transaction(
                txtype="sendfrom",
                from_user_id=origin,
                txhash=outcome,
                txdate=datetime.now(),
                amount=amount,
                currency=COINS[self.coin]["ticker"],
                to_coin_address=destination,
                confirmations=confirmations,
                last_confirmation=last_confirmation
            )
        db.session.add(tx)
        db.session.commit()
        return outcome

    @error_handler
    def rpc_connect(self):
        """Connect to a coin daemon's JSON RPC interface.

        Returns:
          bool: True if successfully connected, False otherwise.

        """
        if self.coin in COINS:
            rpc_url = COINS[self.coin]["rpc-url"] + ":"
            if self.testnet:
                rpc_url += COINS[self.coin]["rpc-port-testnet"]
            else:
                rpc_url += COINS[self.coin]["rpc-port"]
            self.rpc = pyjsonrpc.HttpClient(
                url=rpc_url,
                username=COINS[self.coin]["rpc-user"],
                password=COINS[self.coin]["rpc-password"]
            )
            self.logger.debug(self.coin, "RPC connection ok")
            self.connected = True
        else:
            self.logger.debug(self.coin, "bridge not found")
        return self.connected

    ##################################
    # Wrappers for JSON RPC commands #
    ##################################

    @error_handler
    def getinfo(self):
        """Get basic information for this coin.

        Returns:
          dict: basic coin information, for example:
            {
              "version" : 90201,
              "protocolversion" : 70002,
              "walletversion" : 60000,
              "balance" : 1.53250000,
              "blocks" : 277015,
              "timeoffset" : 0,
              "connections" : 8,
              "proxy" : "",
              "difficulty" : 1.00000000,
              "testnet" : true,
              "keypoololdest" : 1405393929,
              "keypoolsize" : 101,
              "unlocked_until" : 0,
              "paytxfee" : 0.00000000,
              "relayfee" : 0.00001000,
              "errors" : 
            }

        """
        return self.rpc.call("getinfo")

    @error_handler
    def gettransaction(self, txhash):
        """Look up detailed transaction information, using its hash.

        Args:
          txhash (str): transaction hash to be looked up

        Returns:
          dict: details of the transaction.  For example:
            {
              "amount" : 0.00000000,
              "fee" : 0.00000000,
              "confirmations" : 166,
              "blockhash" : "00000000510dcd9863...",
              "blockindex" : 1,
              "blocktime" : 1408759544,
              "txid" : "66d6536bd3c6863d8...",
              "walletconflicts" : [
              ],
              "time" : 1408758352,
              "timereceived" : 1408758352,
              "details" : [
                {
                  "account" : "4",
                  "address" : "n2X1EZS4fAqYiv...",
                  "category" : "send",
                  "amount" : -0.01000000,
                  "fee" : 0.00000000
                },
                {
                  "account" : "4",
                  "address" : "n2X1EZS4fAqYiv...",
                  "category" : "receive",
                  "amount" : 0.01000000
                }
              ],
              "hex" : "0100000001acdb4..."
            }

        """
        return self.rpc.call("gettransaction", txhash)

    @error_handler
    def getaccountaddress(self, user_id=""):
        """Get the coin address associated with a user id.

        If the specified user id does not yet have an address for this
        coin, then generate one.

        Args:
          user_id (str): this user's unique identifier

        Returns:
          str: Base58Check address for this account
        """
        address = self.rpc.call("getaccountaddress", user_id)
        self.logger.debug("Your", self.coin, "address is", address)
        return address
    
    @error_handler
    def getbalance(self, user_id="", as_decimal=True):
        """Calculate the total balance in all addresses belonging to this user.

        Args:
          user_id (str): this user's unique identifier
          as_decimal (bool): balance is returned as a Decimal if True (default)
                             or a string if False

        Returns:
          str or Decimal: this account's total coin balance
        """
        balance = unicode(self.rpc.call("getbalance", user_id))
        self.logger.debug("\"" + user_id + "\"", self.coin, "balance:", balance)
        if as_decimal:
            return Decimal(balance)
        else:
            return balance

    @error_handler
    def getaddressesbyaccount(self, user_id=""):
        """List all addresses associated with this account"""
        return self.rpc.call("getaddressesbyaccount", user_id)

    @error_handler
    def listaddresses(self, user_id=""):
        return self.rpc.getaddressesbyaccount(user_id)

    @error_handler
    def listaccounts(self):
        return self.rpc.call("listaccounts")
    
    @error_handler
    def listtransactions(self, user_id="", count=10, start_at=0):
        """List all transactions associated with this account.

        Args:
          user_id (str): this user's unique identifier
          count (int): number of transactions to return (default=10)
          start_at (int): start the list at this transaction (default=0)

        Returns:
          list [dict]: transactions associated with this user's account
        """
        txlist = self.rpc.call("listtransactions", user_id, count, start_at)
        self.logger.debug("Got transaction list for " + str(user_id))
        return txlist

    @error_handler
    def move(self, fromaccount, toaccount, amount, minconf=1):
        """Send coins between accounts in the same wallet.

        If the receiving account does not exist, it is automatically
        created (but not automatically assigned an address).

        Args:
          fromaccount (str): origin account
          toaccount (str): destination account
          amount (str or Decimal): amount to send (8 decimal points)
          minconf (int): ensure the account has a valid balance using this
                         many confirmations (default=1) 

        Returns:
          bool: True if the coins are moved successfully, False otherwise
        """
        amount = Decimal(amount).quantize(self.quantum, rounding=ROUND_HALF_EVEN)
        return self.rpc.call("move",
            fromaccount, toaccount, float(str(amount)), minconf
        )

    @error_handler
    def sendfrom(self, user_id, dest_address, amount, minconf=1):
        """
        Send coins from user's account.

        Args:
          user_id (str): this user's unique identifier
          dest_address (str): address which is to receive coins
          amount (str or Decimal): amount to send (eight decimal points)
          minconf (int): ensure the account has a valid balance using this
                         many confirmations (default=1)

        Returns:
          str: transaction ID
        """
        amount = Decimal(amount).quantize(self.quantum, rounding=ROUND_HALF_EVEN)
        txhash = self.rpc.call("sendfrom",
            user_id, dest_address, float(str(amount)), minconf
        )
        self.logger.debug("Send %s %s from %s to %s" % (str(amount), self.coin,
                                                        str(user_id), dest_address))
        self.logger.debug("Transaction hash: %s" % txhash)
        return txhash

    @error_handler
    def encryptwallet(self):
        self.rpc.call("encryptwallet", COINS[self.coin]["passphrase"])

    @error_handler
    def walletpassphrase(self, timeout=30):
        try:
            self.rpc.call("walletpassphrase",
                          COINS[self.coin]["passphrase"],
                          int(timeout))
        except:
            self.logger.error("Could not unlock wallet")

    @error_handler
    def walletunlock(self, timeout=30):
        """Unlock wallet.

        Unlocking a wallet allows coins to be spent, messages to be signed,
        and other restricted actions to take place.

        Args:
          timeout (int): how many seconds the wallet will remain unlocked.
                         (default=30)
        """
        return self.walletpassphrase(int(timeout))

    @error_handler
    def walletlock(self):
        """Lock wallet.

        Locking a wallet prohibits certain restricted commands, such as
        spending coins, signing messages, etc.
        """
        self.rpc.call("walletlock")

    @error_handler
    def signmessage(self, address, message):
        """Sign a message with the private key of an address.

        Cryptographically signs a message using ECDSA.  Since this requires
        an address's private key, the wallet must be unlocked first.

        Args:
          address (str): address used to sign the message
          message (str): plaintext message to which apply the signature

        Returns:
          str: ECDSA signature over the message
        """
        signature = self.rpc.call("signmessage", address, message)
        self.logger.debug("Signature: %s" % signature)
        return signature

    @error_handler
    def verifymessage(self, address, signature, message):
        """
        Verifies that a message has been signed by an address.

        Args:
          address (str): address claiming to have signed the message
          signature (str): ECDSA signature
          message (str): plaintext message which was signed

        Returns:
          bool: True if the address signed the message, False otherwise
        """
        verified = self.rpc.call("verifymessage", address, signature, message)
        self.logger.debug("Signature verified: %s" % str(verified))
        return verified

    @error_handler
    def call(self, command, *args):
        """
        Passes an arbitrary command to the coin daemon.

        Args:
          command (str): command to be sent to the coin daemon
        """
        return self.rpc.call(str(command), *args)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
