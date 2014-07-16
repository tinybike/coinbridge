import sys
import cdecimal
sys.modules["decimal"] = cdecimal
import urllib2
import unittest
from decimal import Decimal
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "bridge"))
from bridge import Bridge
import config

class TestBridge(unittest.TestCase):

    def setUp(self):
        config.TESTING = True
        self.user_id = "4"
        self.coin = "Bitcoin"
        self.amount_to_send = 0.0001
        self.testnet = True
        self.address = "n1ZrTB6epfayhzWLhqd2x2whFuSns6Ntgi"
        self.btc_testnet_faucet = "msj42CCGruhRsFrGATiUuh25dtxYtnpbTx"
        self.btc_mainnet = "1Q1wVsNNiUo68caU7BfyFFQ8fVBqxC2DSc"  # localbitcoins address
        self.test_address = "msrKBTfUoQHicmRucsfEYQ5Mbk5niVeWii" # "" account address on testnet
        self.message = "hello world!"
        self.txfields = ("account", "address", "category", "amount",
                         "confirmations", "txid", "walletconflicts",
                         "time", "timereceived")
        self.bridge = Bridge(self.coin)
        self.bridge.rpc_connect(testnet=self.testnet)
        self.bridge.walletlock()
        self.assertIn(self.bridge.coin, config.COINS)

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
        self.bridge.walletunlock(config.COINS[self.bridge.coin]["passphrase"],
                                 config.COINS[self.bridge.coin]["unlock-timeout"])
        txid = self.bridge.sendfrom(self.user_id, self.address, self.amount_to_send)
        self.assertIsNotNone(txid)
        self.assertEqual(type(txid), str)

    def test_walletlock(self):
        """Bridge.walletlock"""
        self.bridge.walletunlock(config.COINS[self.bridge.coin]["passphrase"],
                                 config.COINS[self.bridge.coin]["unlock-timeout"])
        txid = self.bridge.sendfrom(self.user_id, self.address, self.amount_to_send)
        self.assertIsNotNone(txid)
        self.assertEqual(type(txid), str)   
        self.bridge.walletlock()

    def test_sendfrom(self):
        """Bridge.sendfrom"""
        self.bridge.walletunlock(config.COINS[self.bridge.coin]["passphrase"],
                                 config.COINS[self.bridge.coin]["unlock-timeout"])
        txid = self.bridge.sendfrom(self.user_id, self.address, self.amount_to_send)
        self.assertEqual(type(txid), str)

    def test_signmessage(self):
        """Bridge.signmessage"""
        signature = self.bridge.signmessage(self.test_address, self.message)

    def test_verifymessage(self):
        """Bridge.verifymessage"""
        signature = self.bridge.signmessage(self.test_address,
                                            self.message)
        verified = self.bridge.verifymessage(self.test_address,
                                             signature,
                                             self.message)
        self.assertTrue(verification)

    def tearDown(self):
        del self.bridge


if __name__ == "__main__":
    unittest.main()
