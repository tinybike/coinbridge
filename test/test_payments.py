#!/usr/bin/env python
"""Unit tests for Coinbridge.

These tests require you to be running bitcoind.  These tests assume your
bitcoind is connected to the Bitcoin testnet.  Caution: this file includes
tests that transfer/spend Bitcoins!

To obtain some testnet Bitcoins, visit TP's Testnet Faucet, at
http://tpfaucet.appspot.com/.  Please remember to return your testnet BTC
to msj42CCGruhRsFrGATiUuh25dtxYtnpbTx when you are done testing!
"""
from __future__ import division, unicode_literals
try:
    import sys
    import cdecimal
    sys.modules["decimal"] = cdecimal
except:
    pass
import os
import unittest
from decimal import Decimal, ROUND_HALF_EVEN

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(HERE, os.pardir))

from coinbridge import *

class TestBridge(unittest.TestCase):

    def setUp(self):
        self.user_id = "testaccount1"
        self.other_user_id = "testaccount2"
        self.coin = "Bitcoin"
        self.message = "hello world!"   # used for signature testing
        self.txfields = ("account", "category", "amount", "time")
        self.quantum = Decimal("1e-"+str(COINS[self.coin.lower()]["decimals"]))
        self.amount_to_send = Decimal("0.01").quantize(self.quantum,
                                                       rounding=ROUND_HALF_EVEN)
        self.txfee = Decimal(COINS[self.coin.lower()]["txfee"])
        self.bridge = Bridge(coin=self.coin, testnet=True,
                             reconnect=False, testing=True)
        self.assertFalse(self.bridge.reconnect)
        self.assertEqual(self.bridge.quantum, self.quantum)
        self.assertTrue(self.bridge.testnet)
        self.assertEqual(self.bridge.coin, u"bitcoin")
        self.assertTrue(self.bridge.connected)
        self.user_address = self.bridge.getaccountaddress(self.user_id)
        self.other_user_address = self.bridge.getaccountaddress(self.other_user_id)
        self.bridge.walletlock()
        self.btc_testnet_faucet = "msj42CCGruhRsFrGATiUuh25dtxYtnpbTx"

    def test_sendfrom(self):
        for destination in (self.other_user_address, self.btc_testnet_faucet):
            old_balance, new_balance = self.sendfrom(destination)
            spent = old_balance - new_balance
            # print("Intended to send:", str(self.amount_to_send))
            # print("Actual amount (including fee):", str(spent))
            # print("Fee paid:", str(spent - self.amount_to_send))
            self.assertEqual(spent - self.amount_to_send, self.txfee)

    def test_move(self):
        for destination in (self.other_user_id, self.user_address):
            old_balance, new_balance = self.move(destination)
            spent = old_balance - new_balance
            # print("Intended to send:", str(self.amount_to_send))
            # print("Actual amount (including fee):", str(spent))
            # print("Fee paid:", str(spent - self.amount_to_send))
            self.assertEqual(spent, self.amount_to_send)
        self.assertRaises(Exception, self.move(destination))

    def test_payment(self):
        # "move" payments: no transaction fee
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
        # print("Intended to send:", str(self.amount_to_send))
        # print("Actual amount (including fee):", str(spent))
        # print("Fee paid:", str(spent - self.amount_to_send))
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
        # print("Intended to send:", str(self.amount_to_send))
        # print("Actual amount (including fee):", str(spent))
        # print("Fee paid:", str(spent - self.amount_to_send))
        self.assertEqual(spent - self.amount_to_send, self.txfee)
        self.assertEqual(old_balance - new_balance,
                         self.amount_to_send + self.txfee)

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

    def move(self, destination):
        old_balance = self.bridge.getbalance(self.user_id)
        with self.bridge.openwallet():
            result = self.bridge.move(self.user_id, destination,
                                      self.amount_to_send)
        new_balance = self.bridge.getbalance(self.user_id)
        return old_balance, new_balance

    def tearDown(self):
        del self.bridge


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBridge)
    unittest.TextTestRunner(verbosity=2).run(suite)
