from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    asset = Column(String, nullable=False)
    type = Column(String, nullable=False)
    entry = Column(Float, nullable=False)
    break_even = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profits = Column(String, nullable=False)
    status = Column(String, default='open', nullable=False)