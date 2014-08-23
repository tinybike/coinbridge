"""Bridge between Bitcoin and PostgreSQL.

Connects the Bitcoin daemon (bitcoind) and a local PostgreSQL
database. Listens for transaction confirmations and automatically
updates a transactions table in your database.

Usage:
    from coinbridge import Bridge
    bitcoin_bridge = Bridge()
    bitcoin_bridge.payment(from_account, to_account, amount)
"""
try:
    import sys
    import cdecimal
    sys.modules["decimal"] = cdecimal
except:
    pass

__title__      = "CoinBridge"
__version__    = "0.1"
__author__     = "Jack Peterson"
__copyright__  = "Copyright 2014, Jack Peterson"
__license__    = "MIT"
__maintainer__ = "Jack Peterson"
__email__      = "jack@tinybike.net"

from .bridge import Bridge
