#!/usr/bin/env python
from __future__ import division
from bridge import Bridge
from decimal import Decimal
import config

config.TESTING = True
faucet = "msj42CCGruhRsFrGATiUuh25dtxYtnpbTx"

b = Bridge()
b.rpc_connect(testnet=True)

print b.getinfo()

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
