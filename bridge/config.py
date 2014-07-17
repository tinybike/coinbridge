import os

if os.environ.get("DEPLOY_ENV", "production") == "development":
    DEPLOY_ENV = "development"
    DEBUG = True
else:
    DEPLOY_ENV = "production"
    DEBUG = False

TESTING = False

POSTGRES = {
    "host": "localhost",
    "database": "coinbridge",
    "user": "coinbridge",
    "password": "overpass",
    "driver": "psycopg2",
    "port": 5432,
}
POSTGRES["urlstring"] = (
    "postgresql+" + POSTGRES["driver"] + "://" +
    POSTGRES["user"] + ":" + POSTGRES["password"] + "@" +
    POSTGRES["host"] + "/" + POSTGRES["database"]
)

# Coin daemon info
COINS = {
    "bitcoin": {
        "ticker": "BTC",
        "confirmations": 6,
        "network-port": "8333",
        "network-port-testnet": "18333",
        "rpc-url": "http://127.0.0.1",
        "rpc-port": "8332",
        "rpc-port-testnet": "18332",
        "rpc-user": "ZTwijIDcaRCY",
        "rpc-password": "qBrbIrxGlUhh797oIOwKRN7XN7lavBAq",
        "passphrase": "uMrTVAOVSuoOkqEPcgtyFdiWWzlZOYX5",
        "unlock-timeout": 30,
        "decimals": 8,
        "txfee": "0.0001",
    }
}
