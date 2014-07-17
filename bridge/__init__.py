import sys
import cdecimal
sys.modules["decimal"] = cdecimal

__title__       =       "CoinBridge"
__version__     =       "0.0.1"
__author__      =       "Jack Peterson"
__license__     =       "None"

from .bridge import Bridge
