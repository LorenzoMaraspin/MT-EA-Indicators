class TradeUpdate():
    def __init__(self, trade_id: int , update_text: str, new_value: int, order_id: str, id: int = None):
        self.trade_id = trade_id
        self.update_text = update_text
        self.new_value = new_value
        self.order_id = order_id
        self.id = id
