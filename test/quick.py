#!/usr/bin/env python
import sys
import cdecimal
sys.modules["decimal"] = cdecimal
from decimal import Decimal
import os
from pprint import pprint
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "bridge"))
from bridge import Bridge
import config

config.TESTING = True
faucet = "msj42CCGruhRsFrGATiUuh25dtxYtnpbTx"

b = Bridge()
b.rpc_connect(testnet=True)

pprint(b.getinfo())

old_balance = b.getbalance("jack")

addr = b.listaddresses("jack")
for a in addr:
    print a

amount = Decimal("0.01")
b.walletunlock(timeout=60)
print "Sending 0.01 BTC back to the testnet faucet"
b.sendfrom("jack", faucet, amount)
b.walletlock()

new_balance = b.getbalance("jack")

spent = old_balance - new_balance
print "Intended to send:", str(amount)
print "Actual amount (including fee):", str(spent)
print "Fee paid:", str(spent - amount)
