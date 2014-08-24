#!/usr/bin/env python
"""Unit tests for Coinbridge.

These tests require you to be running bitcoind.  These tests assume your
bitcoind is connected to the Bitcoin testnet.  This file only includes
tests that do not transfer/spend Bitcoins.

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

    def test_getinfo(self):
        info = self.bridge.getinfo()
        expected = ("version", "protocolversion", "walletversion", "balance",
                    "blocks", "timeoffset", "connections", "proxy", "difficulty",
                    "testnet", "keypoololdest", "keypoolsize", "unlocked_until",
                    "paytxfee", "relayfee", "errors")
        for x in expected:
            self.assertIn(x, info)
        self.assertGreater(info["version"], 90000)
        self.assertGreater(info["balance"], 0)
        self.assertGreater(info["connections"], 0)
        self.assertGreaterEqual(info["difficulty"], 1.0)
        self.assertTrue(info["testnet"])

    def test_getbalance(self):
        balance = self.bridge.getbalance(self.user_id, as_decimal=True)
        self.assertIsNotNone(balance)
        self.assertGreaterEqual(balance, Decimal("0"))
        self.assertEqual(type(balance), Decimal)
        balance = self.bridge.getbalance(self.user_id, as_decimal=False)
        self.assertIsNotNone(balance)
        self.assertGreaterEqual(balance, Decimal("0"))
        self.assertEqual(type(balance), unicode)

    def test_getaccountaddress(self):
        address = self.bridge.getaccountaddress(self.user_id)
        self.assertIsNotNone(address)

    def test_listtransactions(self):
        txlist = self.bridge.listtransactions(self.user_id)
        self.assertIsNotNone(txlist)
        self.assertEqual(type(txlist), list)
        for tx in txlist:
            self.assertEqual(type(tx), dict)
            for field in self.txfields:
                self.assertIn(field, tx)

    def test_walletunlock(self):
        self.bridge.walletunlock()
        signature = self.bridge.signmessage(self.user_address, self.message)
        self.assertIsNotNone(signature)
        self.assertEqual(type(signature), str)
        verified = self.bridge.verifymessage(self.user_address,
                                             signature,
                                             self.message)
        self.assertTrue(verified)

    def test_walletlock(self):
        self.bridge.walletunlock()
        signature = self.bridge.signmessage(self.user_address, self.message)
        self.assertIsNotNone(signature)
        self.assertEqual(type(signature), str)
        verified = self.bridge.verifymessage(self.user_address,
                                             signature,
                                             self.message)
        self.assertTrue(verified)
        self.bridge.walletlock()
        self.assertRaises(Exception, self.bridge.signmessage(self.user_address,
                                                             self.message))

    def test_signmessage(self):
        with self.bridge.openwallet():
            signature = self.bridge.signmessage(self.user_address,
                                                self.message)
        self.assertIsNotNone(signature)
        self.assertEqual(type(signature), str)

    def test_verifymessage(self):
        with self.bridge.openwallet():
            signature = self.bridge.signmessage(self.user_address,
                                                self.message)
            self.assertIsNotNone(signature)
            verified = self.bridge.verifymessage(self.user_address,
                                                 signature,
                                                 self.message)
        self.assertTrue(verified)

    def tearDown(self):
        del self.bridge


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBridge)
    unittest.TextTestRunner(verbosity=2).run(suite)
