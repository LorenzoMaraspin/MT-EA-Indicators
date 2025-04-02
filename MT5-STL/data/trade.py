class Trade:
    def __init__(self,
                 msg_id: int,
                 order_id: int,
                 account_id: int,
                 symbol: str,
                 direction: str,
                 volume: float,
                 stop_loss: float,
                 take_profit: float,
                 entry_price: float,
                 break_even: float,
                 status: str,
                 trade_id: int = None):
        self.msg_id = msg_id
        self.symbol = symbol
        self.direction = direction
        self.volume = volume
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry_price = entry_price
        self.break_even = break_even
        self.order_id = order_id
        self.status = status
        self.account_id = account_id
        self.trade_id = trade_id

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'direction': self.direction,
            'volume': self.volume,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_price': self.entry_price,
            'break_even': self.break_even,
            'status': self.status,
            'account_id': self.account_id,
            'order_id': self.order_id
        }