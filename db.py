from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Table, Text, Float
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import config

Base = declarative_base()

class Transaction(Base):
    """"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    txhash = Column(String(100))
    txdate = Column(DateTime, default=func.transaction_timestamp())
    amount = Column(Numeric(precision=23, scale=8, asdecimal=True))
    currency = Column(String(10), nullable=False)
    coin_address = Column(String(100))
    inbound = Column(Boolean) # True for inbound bridge, False for outbound, NULL for non-bridge
    confirmations = Column(Integer, default=0)
    last_confirmation = Column(DateTime)


def start_session(get_engine=False):
    engine = create_engine(config.POSTGRES["urlstring"],
                           isolation_level="SERIALIZABLE",
                           echo=False)
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
