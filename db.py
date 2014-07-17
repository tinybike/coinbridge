from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Table, Text, Float
from sqlalchemy import create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import config

Base = declarative_base()

class Transaction(Base):
    """"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    txtype = Column(String(25), default="internal")
    from_user_id = Column(Integer)
    to_user_id = Column(Integer)
    txhash = Column(String(100))
    txdate = Column(DateTime, default=func.transaction_timestamp())
    amount = Column(Numeric(precision=23, scale=8, asdecimal=True))
    currency = Column(String(10), nullable=False)
    from_coin_address = Column(String(100))
    to_coin_address = Column(String(100))
    confirmations = Column(Integer)
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
