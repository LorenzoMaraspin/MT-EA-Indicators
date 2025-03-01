from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TradeUpdate(Base):
    __tablename__ = 'trade_updates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey('trades.id'), nullable=False)
    update_text = Column(String, nullable=False)
    new_value = Column(Float, nullable=False)