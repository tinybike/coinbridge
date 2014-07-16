#!/usr/bin/env python
"""
Coin bridges for fun and profit
Usage:
    from bridge import Bridge
    bitcoin_bridge = Bridge("Bitcoin")
    ...
@author jack@tinybike.net (Jack Peterson)
@license None yet, you dirty thief
"""
import urllib2
from decimal import Decimal
import pyjsonrpc
import config
import db

db.init()

class Bridge(object):

    def __init__(self, coin, logfile="log/bridge.log"):
        self.coin = coin.lower()
        self.connected = False
        self.log = logfile

    ##################################
    # Wrappers for JSON RPC commands #
    ##################################

    @error_handler("Bridge.rpc_connect")
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
                print self.coin, "RPC connection ok"
            self.connected = True
        else:
            if config.DEBUG:
                print self.coin, "bridge not found"
        return self.connected

    @error_handler("Bridge.getinfo")
    def getinfo(self):
        """Get basic info for this coin"""
        return self.rpc.call("getinfo")

    @error_handler("Bridge.getaccountaddress")
    def getaccountaddress(self, user_id):
        """
        Get the coin address associated with a user id.  If the user id does
        not yet have an address for this coin, generate one.

        Args:
          user_id (str): this user's unique identifier

        Returns:
          str: address for this coin.
        """
        address = self.rpc.call("getaccountaddress", user_id)
        if config.DEBUG:
            print "Your", self.coin, "address is", address
        return address
    
    @error_handler("Bridge.getbalance")
    def getbalance(self, user_id, as_decimal=False):
        """
        Calculate the total balance in all addresses belonging to this user.

        Args:
          user_id (str): this user's unique identifier

        Returns:
          str: this account's total coin balance
        """
        balance = str(self.rpc.call("getbalance", user_id))
        if config.DEBUG:
            print user_id, self.coin, "balance:", balance
        if as_decimal:
            return Decimal(balance)
        else:
            return balance
    
    @error_handler("Bridge.listtransactions")
    def listtransactions(self, user_id, count=10, start_at=0):
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
        if config.DEBUG:
            print "Got transaction list for", user_id
        return txlist

    @error_handler("Bridge.inbound")
    def inbound(self, user_id):
        # get info from walletnotify?
        pass

    @error_handler("Bridge.sendfrom")
    def sendfrom(self, user_id, address, amount, minconf=1):
        """
        Send coins from user's account.

        Args:
          user_id (str): this user's unique identifier
          address (str): address which is to receive coins
          amount (eight decimal points): amount to send
          minconf (int): ensure the account has a valid balance using this
                         many confirmations (default=1)

        Returns:
          str: transaction ID
        """
        txid = self.rpc.call("sendfrom", user_id, address, amount, minconf)
        if config.DEBUG:
            print "Sent", amount, self.coin, "from", user_id, "to", address
            print "Transaction ID:", txid
        return txid

    @error_handler("Bridge.walletpassphrase")
    def walletpassphrase(self, passphrase, timeout):
        try:
            self.rpc.call("walletpassphrase",
                          config.COINS[self.coin]["passphrase"],
                          timeout)
        except urllib2.HTTPError:
            print "Could not unlock wallet"
            if config.TESTING:
                raise

    @error_handler("Bridge.walletunlock")
    def walletunlock(self, passphrase, timeout):
        self.walletpassphrase(passphrase, int(timeout))

    @error_handler("Bridge.walletlock")
    def walletlock(self):
        self.rpc.call("walletlock")

    @error_handler("Bridge.signmessage")
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
        if config.DEBUG:
            print "Signature:", signature
        return signature

    @error_handler("Bridge.verifymessage")
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
        if config.DEBUG:
            print "Signature verified:", verified
        return verified

    @error_handler("Bridge.call")
    def call(self, command, *args):
        return self.rpc.call(str(command), *args)


if __name__ == '__main__':
    bridge = Bridge("Bitcoin")
