#!/usr/bin/env python
"""Unit tests for CoinBridge.

For obvious reasons, these tests are configured assuming that your bitcoind
is connected to the Bitcoin testnet.  To obtain some testnet Bitcoins, 
visit TP's Testnet Faucet: http://tpfaucet.appspot.com/.  Please remember to
return them when you are done testing!
"""
try:
    import sys
    import cdecimal
    sys.modules["decimal"] = cdecimal
except:
    pass
import os
import unittest
from decimal import Decimal, ROUND_HALF_EVEN

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "bridge"))

from bridge import Bridge, db
import config

class TestBridge(unittest.TestCase):

    def setUp(self):
        config.TESTING = True
        self.user_id = "4"
        self.other_user_id = "5"
        self.coin = "Bitcoin"
        self.quantum = Decimal("1e-"+str(config.COINS[self.coin.lower()]["decimals"]))
        self.amount_to_send = Decimal("0.01").quantize(self.quantum,
                                                       rounding=ROUND_HALF_EVEN)
        self.testnet = True
        self.address = "n2X1EZS4fAqYivnzQFUatpx4j3URyUWnBP"
        self.btc_testnet_faucet = "msj42CCGruhRsFrGATiUuh25dtxYtnpbTx"
        self.btc_mainnet = "1Q1wVsNNiUo68caU7BfyFFQ8fVBqxC2DSc"  # localbitcoins address
        self.test_address = "msrKBTfUoQHicmRucsfEYQ5Mbk5niVeWii" # "" account address on testnet
        self.message = "hello world!"
        self.txfields = ("account", "category", "amount", "time")
        self.txfee = Decimal(config.COINS[self.coin.lower()]["txfee"])
        self.bridge = Bridge()
        self.bridge.rpc_connect(testnet=self.testnet)
        self.bridge.walletlock()
        self.assertIn(self.bridge.coin, config.COINS)

    def test_payment(self):
        """Bridge.payment"""
        # "move" payments: no transaction fee
        # me -> me
        old_balance = self.bridge.getbalance(self.user_id)
        old_accounts = len(self.bridge.listaccounts())
        with self.bridge.openwallet():
            result = self.bridge.payment(self.user_id,
                                         self.address,
                                         self.amount_to_send)
        self.assertTrue(result)
        new_balance = self.bridge.getbalance(self.user_id)
        new_accounts = len(self.bridge.listaccounts())
        self.assertEqual(old_accounts, new_accounts)
        spent = old_balance - new_balance
        print "Intended to send:", str(self.amount_to_send)
        print "Actual amount (including fee):", str(spent)
        print "Fee paid:", str(spent - self.amount_to_send)
        self.assertEqual(spent, 0)
        self.assertEqual(old_balance, new_balance)
        # me -> other account in wallet
        old_balance = self.bridge.getbalance(self.user_id)
        old_accounts = len(self.bridge.listaccounts())
        with self.bridge.openwallet():
            result = self.bridge.payment(self.user_id,
                                         self.other_user_id,
                                         self.amount_to_send)
        self.assertTrue(result)
        new_balance = self.bridge.getbalance(self.user_id)
        new_accounts = len(self.bridge.listaccounts())
        self.assertEqual(old_accounts, new_accounts)
        spent = old_balance - new_balance
        print "Intended to send:", str(self.amount_to_send)
        print "Actual amount (including fee):", str(spent)
        print "Fee paid:", str(spent - self.amount_to_send)
        self.assertEqual(spent, self.amount_to_send)
        self.assertEqual(old_balance - new_balance, self.amount_to_send)
        # "sendfrom" payments: transaction fee
        # me -> outside account
        old_balance = self.bridge.getbalance(self.user_id)
        old_accounts = len(self.bridge.listaccounts())
        with self.bridge.openwallet():
            txhash = self.bridge.payment(self.user_id,
                                         self.btc_testnet_faucet,
                                         self.amount_to_send)
        self.assertIsNotNone(txhash)
        self.assertEqual(type(txhash), str)
        new_balance = self.bridge.getbalance(self.user_id)
        new_accounts = len(self.bridge.listaccounts())
        self.assertEqual(old_accounts, new_accounts)
        spent = old_balance - new_balance
        print "Intended to send:", str(self.amount_to_send)
        print "Actual amount (including fee):", str(spent)
        print "Fee paid:", str(spent - self.amount_to_send)
        self.assertEqual(spent - self.amount_to_send, self.txfee)
        self.assertEqual(old_balance - new_balance,
                         self.amount_to_send + self.txfee)

    def test_getinfo(self):
        """Bridge.getinfo"""
        self.bridge.getinfo()

    def test_getbalance(self):
        """Bridge.getbalance"""
        self.bridge.getbalance(self.user_id)

    def test_getaccountaddress(self):
        """Bridge.getaccountaddress"""
        address = self.bridge.getaccountaddress(self.user_id)

    def test_listtransactions(self):
        """Bridge.listtransactions"""
        txlist = self.bridge.listtransactions(self.user_id)
        self.assertIsNotNone(txlist)
        self.assertEqual(type(txlist), list)
        for tx in txlist:
            self.assertEqual(type(tx), dict)
            for field in self.txfields:
                self.assertIn(field, tx)

    def test_walletunlock(self):
        """Bridge.walletunlock"""
        self.bridge.walletunlock()
        result = self.bridge.payment(self.user_id,
                                     self.address,
                                     self.amount_to_send)
        self.assertTrue(result)

    def test_walletlock(self):
        """Bridge.walletlock"""
        self.bridge.walletunlock()
        result = self.bridge.payment(self.user_id,
                                     self.address,
                                     self.amount_to_send)
        self.assertTrue(result)
        self.bridge.walletlock()
        self.assertRaises(Exception, self.bridge.payment(self.user_id,
                                                         self.address,
                                                         self.amount_to_send))

    def sendfrom(self, destination):
        old_balance = self.bridge.getbalance(self.user_id)
        with self.bridge.openwallet():
            txhash = self.bridge.sendfrom(self.user_id,
                                          destination,
                                          self.amount_to_send)
        self.assertIsNotNone(txhash)
        self.assertEqual(type(txhash), str)
        new_balance = self.bridge.getbalance(self.user_id)
        return old_balance, new_balance

    def test_sendfrom(self):
        """Bridge.sendfrom"""
        for destination in (self.address, self.btc_testnet_faucet):
            old_balance, new_balance = self.sendfrom(destination)
            spent = old_balance - new_balance
            print "Intended to send:", str(self.amount_to_send)
            print "Actual amount (including fee):", str(spent)
            print "Fee paid:", str(spent - self.amount_to_send)
            self.assertEqual(spent - self.amount_to_send, self.txfee)

    def move(self, destination):
        old_balance = self.bridge.getbalance(self.user_id)
        with self.bridge.openwallet():
            result = self.bridge.move(self.user_id, destination,
                                      self.amount_to_send)
        new_balance = self.bridge.getbalance(self.user_id)
        return old_balance, new_balance

    def test_move(self):
        """Bridge.move"""
        for destination in (self.other_user_id, self.test_address):
            old_balance, new_balance = self.move(destination)
            spent = old_balance - new_balance
            print "Intended to send:", str(self.amount_to_send)
            print "Actual amount (including fee):", str(spent)
            print "Fee paid:", str(spent - self.amount_to_send)
            self.assertEqual(spent, self.amount_to_send)
        self.assertRaises(Exception, self.move(destination))

    def test_signmessage(self):
        """Bridge.signmessage"""
        with self.bridge.openwallet():
            signature = self.bridge.signmessage(self.test_address,
                                                self.message)
        self.assertIsNotNone(signature)
        self.assertEqual(type(signature), str)

    def test_verifymessage(self):
        """Bridge.verifymessage"""
        with self.bridge.openwallet():
            signature = self.bridge.signmessage(self.test_address,
                                                self.message)
            self.assertIsNotNone(signature)
            verified = self.bridge.verifymessage(self.test_address,
                                                 signature,
                                                 self.message)
        self.assertTrue(verified)

    def tearDown(self):
        del self.bridge


if __name__ == "__main__":
    unittest.main()
