#!/usr/bin/env python

import os
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Table, Text, Float, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import MetaData

Base = declarative_base()

try:
    HERE = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(HERE, "data", "pg.cfg")) as pgfile:
        POSTGRES = pgfile.readline().strip().split(':')
except:
    pgpasspath = os.environ.get("PGPASSFILE")
    with open(pgpasspath) as pgpassfile:
        for line in pgpassfile:
            pgpass = line.strip().split(':')
            if pgpass[2] == "coinbridge":
                POSTGRES = pgpass

urlstring = "postgresql+psycopg2://" + POSTGRES[2] + ":" +\
    POSTGRES[4] + "@" + POSTGRES[0] + "/" + POSTGRES[3]

class Transaction(Base):

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    txtype = Column(String(25), default="internal")
    from_user_id = Column(String(50))
    to_user_id = Column(String(50))
    txhash = Column(String(100))
    txdate = Column(DateTime, default=func.transaction_timestamp())
    amount = Column(Numeric(precision=23, scale=8, asdecimal=True))
    currency = Column(String(10), nullable=False)
    from_coin_address = Column(String(100))
    to_coin_address = Column(String(100))
    confirmations = Column(Integer)
    last_confirmation = Column(DateTime)


def start_session(get_engine=False):
    engine = create_engine(urlstring, echo=False)
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    if get_engine:
        return engine, session
    return session

def init():
    global engine
    global session
    engine, session = start_session(get_engine=True)

if __name__ == "__main__":
    pass
