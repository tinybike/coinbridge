#!/usr/bin/env python
try:
    import sys
    import cdecimal
    sys.modules["decimal"] = cdecimal
except:
    pass
import os
from decimal import Decimal
from pprint import pprint

sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir, "bridge"))

from bridge import Bridge
import config

config.TESTING = True

faucet = "msj42CCGruhRsFrGATiUuh25dtxYtnpbTx"
jck_address = "mu7MHxcjxt8eSor7juNTXRdSNzA4tkn7om"

b = Bridge()
b.rpc_connect(testnet=True)

pprint(b.getinfo())

old_balance = b.getbalance("jack")

addr = b.listaddresses("jack")
for a in addr:
    print a

amount = Decimal("0.01")

print
print "Sending 0.01 BTC back to the testnet faucet"
with b.openwallet():
    b.sendfrom("jack", faucet, amount)
new_balance = b.getbalance("jack")
spent = old_balance - new_balance
print "Intended to send:", str(amount)
print "Actual amount (including fee):", str(spent)
print "Fee paid:", str(spent - amount)

print

old_balance = b.getbalance("jack")
print "Sending 0.01 BTC from \"jack\" to \"jck\""
b.payment("jack", "jck", amount)
new_balance = b.getbalance("jack")
spent = old_balance - new_balance
print "Intended to send:", str(amount)
print "Actual amount (including fee):", str(spent)
print "Fee paid:", str(spent - amount)
print
