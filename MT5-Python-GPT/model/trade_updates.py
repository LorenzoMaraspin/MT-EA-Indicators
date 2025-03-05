class TradeUpdate():
    def __init__(self, trade_id: int , update_text: str, new_value: int, id: int = None):
        self.trade_id = trade_id
        self.update_text = update_text
        self.new_value = new_value
        self.id = id
