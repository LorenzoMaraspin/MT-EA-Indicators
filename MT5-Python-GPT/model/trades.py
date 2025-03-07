class Trade():
    def __init__(self,
                 message_id: int,
                 asset: str,
                 type: str,
                 volume: float,
                 stop_loss: float,
                 take_profit: float,
                 entry: float,
                 break_even: float,
                 order_id: str,
                 status: str,
                 id: str = None):
        self.message_id = message_id
        self.asset = asset
        self.type = type
        self.volume = volume
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry = entry
        self.break_even = break_even
        self.order_id = order_id
        self.status = status
        self.id = id

    def to_dict(self):
        return {
            'asset': self.asset,
            'type': self.type,
            'volume': self.volume,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry': self.entry,
            'break_even': self.break_even,
            'status': self.status
        }