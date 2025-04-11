class TradeUpdate:
    def __init__(
            self,
            trade_id: int,
            order_id: int,
            account_id: int,
            update_action: str,
            update_body: str,
            trade_update_id: int = None
    ):
        self.trade_id = trade_id
        self.update_action = update_action
        self.update_body = update_body
        self.order_id = order_id
        self.trade_update_id = trade_update_id
        self.account_id = account_id

    def to_dict(self):
        return {
            'trade_id': self.trade_id,
            'update_action': self.update_action,
            'update_body': self.update_body,
            'order_id': self.order_id,
            'account_id': self.account_id
        }
