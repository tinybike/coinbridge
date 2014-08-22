"""
Bridge class: comprehensive wrappers for JSON-RPC functionality
"""
import os
import sys
import urllib2
import json
import time
from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN
from contextlib import contextmanager
import pyjsonrpc
import logging
from errorhandler import error_handler
import config
import db

db.init()
logging.basicConfig(level=logging.INFO)

class Bridge(object):

    def __init__(self, coin="Bitcoin"):
        self.coin = coin.lower()
        self.connected = False
        self.quantum = Decimal("1e-"+str(config.COINS[self.coin]["decimals"]))
        self.logger = logging.getLogger(__name__)

    @contextmanager
    def openwallet(self):
        self.walletunlock()
        yield
        self.walletlock()

    @error_handler
    def payment(self, origin, destination, amount):
        """
        Send coins from origin to destination. Calls record_tx to log the
        transaction to database.

        Args:
          origin (str): user_id of the sender
          destination (str): coin address or user_id of the recipient
          amount (str, Decimal, number): amount to send

        Returns:
          bool: True if successful, False otherwise
        """
        attempts = 0
        while not self.connected:
            attempts += 1
            self.rpc_connect()
            if attempts > 5:
                coin_data = json.dumps(config.COINS[self.coin],
                                       indent=3, sort_keys=True)
                could_not_connect = (
                    "Could not create HTTP RPC connection "
                    "to %s daemon using config:\n%s\nIs the "
                    "daemon running?"
                ) % (self.coin, coin_data)
                raise Exception(could_not_connect)
            time.sleep(5)
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
        """Record transaction in the database."""
        # "move" commands
        if destination_id:
            tx = db.Transaction(
                txtype="move",
                from_user_id=origin,
                to_user_id=destination_id,
                txdate=datetime.now(),
                amount=amount,
                currency=config.COINS[self.coin]["ticker"],
                to_coin_address=destination,
            )
        # "sendfrom" commands
        else:
            self.logger.info(self.gettransaction(outcome))
            confirmations = self.gettransaction(outcome)["confirmations"]
            last_confirmation = datetime.now() if confirmations else None
            tx = db.Transaction(
                txtype="sendfrom",
                from_user_id=origin,
                txhash=outcome,
                txdate=datetime.now(),
                amount=amount,
                currency=config.COINS[self.coin]["ticker"],
                to_coin_address=destination,
                confirmations=confirmations,
                last_confirmation=last_confirmation
            )
        db.session.add(tx)
        db.session.commit()
        return outcome

    ##################################
    # Wrappers for JSON RPC commands #
    ##################################

    @error_handler
    def rpc_connect(self, testnet=False):
        """
        Connect to a coin daemon's JSON RPC interface.

        Args:
          testnet (bool): True for the testnet, False for the mainnet

        Returns:
          bool: True if successfully connected, False otherwise.
        """
        if self.coin in config.COINS:
            rpc_url = config.COINS[self.coin]["rpc-url"] + ":"
            if testnet:
                rpc_url += config.COINS[self.coin]["rpc-port-testnet"]
            else:
                rpc_url += config.COINS[self.coin]["rpc-port"]
            self.rpc = pyjsonrpc.HttpClient(
                url=rpc_url,
                username=config.COINS[self.coin]["rpc-user"],
                password=config.COINS[self.coin]["rpc-password"]
            )
            if config.DEBUG:
                self.logger.debug(self.coin, "RPC connection ok")
            self.connected = True
        else:
            if config.DEBUG:
                self.logger.debug(self.coin, "bridge not found")
        return self.connected

    @error_handler
    def getinfo(self):
        """Get basic info for this coin"""
        return self.rpc.call("getinfo")

    @error_handler
    def gettransaction(self, txhash):
        """
        Transaction data for a specified hash
        """
        return self.rpc.call("gettransaction", txhash)

    @error_handler
    def getaccountaddress(self, user_id=""):
        """
        Get the coin address associated with a user id.  If the user id does
        not yet have an address for this coin, generate one.

        Args:
          user_id (str): this user's unique identifier

        Returns:
          str: address for this coin.
        """
        address = self.rpc.call("getaccountaddress", user_id)
        self.logger.debug("Your", self.coin, "address is", address)
        return address
    
    @error_handler
    def getbalance(self, user_id="", as_decimal=True):
        """
        Calculate the total balance in all addresses belonging to this user.

        Args:
          user_id (str): this user's unique identifier
          as_decimal (bool): balance is returned as a Decimal if True (default)
                             or a string if False

        Returns:
          str: this account's total coin balance
        """
        balance = str(self.rpc.call("getbalance", user_id))
        self.logger.debug("\"" + user_id + "\"", self.coin, "balance:", balance)
        if as_decimal:
            return Decimal(balance)
        else:
            return balance

    @error_handler
    def getaddressesbyaccount(self, user_id=""):
        """
        List all addresses associated with this account
        """
        return self.rpc.call("getaddressesbyaccount", user_id)

    @error_handler
    def listaddresses(self, user_id=""):
        return self.rpc.getaddressesbyaccount(user_id)

    @error_handler
    def listaccounts(self):
        return self.rpc.call("listaccounts")
    
    @error_handler
    def listtransactions(self, user_id="", count=10, start_at=0):
        """
        List all transactions associated with this account.

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
        """
        Send coins between accounts in the same wallet.  If the receiving
        account does not exist, it is automatically created (but not
        automatically assigned an address).

        Args:
          fromaccount (str): origin account
          toaccount (str): destination account
          amount (str or Decimal): amount to send (8 decimal points)
          minconf (int): ensure the account has a valid balance using this
                         many confirmations (default=1) 

        Returns:
          str
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
        # base_unit_amount = amount * Decimal("1e" + str(config.COINS[self.coin]["decimals"]))
        # priority = sum(base_unit_amount * input_age)/size_in_bytes
        txhash = self.rpc.call("sendfrom",
            user_id, dest_address, float(str(amount)), minconf
        )
        self.logger.debug("Send %s %s from %s to %s" % (str(amount), self.coin,
                                                        str(user_id), dest_address))
        self.logger.debug("Transaction hash: %s" % txhash)
        return txhash

    @error_handler
    def encryptwallet(self):
        self.rpc.call("encryptwallet", config.COINS[self.coin]["passphrase"])

    @error_handler
    def walletpassphrase(self, timeout=30):
        try:
            self.rpc.call("walletpassphrase",
                          config.COINS[self.coin]["passphrase"],
                          int(timeout))
        except:
            self.logger.warn("Could not unlock wallet")
            if config.TESTING: raise

    @error_handler
    def walletunlock(self, timeout=30):
        return self.walletpassphrase(int(timeout))

    @error_handler
    def walletlock(self):
        self.rpc.call("walletlock")

    @error_handler
    def signmessage(self, address, message):
        """
        Sign a message with the private key of an address.

        Args:
          address (str): address used to sign the message
          message (str): plaintext message to which apply the signature

        Returns:
          str: message signed with ECDSA signature
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
        return self.rpc.call(str(command), *args)


if __name__ == "__main__":
    pass
