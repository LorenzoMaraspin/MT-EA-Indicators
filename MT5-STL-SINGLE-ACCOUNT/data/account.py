class Account:
    def __init__(self,
                 mt5_account_id: int,
                 mt5_server: str,
                 mt5_broker: str,
                 mt5_balance: float,
                 mt5_password: str,
                 environment: str,
                 tg_id: str,
                 tg_phone: str,
                 tg_session: str,
                 tg_channels: str,
                 tg_hash: str,
                 symbol_config: list = None):
        self.mt5_account_id = mt5_account_id
        self.mt5_server = mt5_server
        self.mt5_broker = mt5_broker
        self.mt5_balance = mt5_balance
        self.mt5_password = mt5_password
        self.environment = environment
        self.tg_id = tg_id
        self.tg_phone = tg_phone
        self.tg_session = tg_session
        self.tg_channels =  [int(channel) for channel in tg_channels.split(",")]
        self.tg_hash = tg_hash
        self.symbol_config = symbol_config
    def to_dict(self):
        return {
            'mt5_account_id': self.mt5_account_id,
            'mt5_server': self.mt5_server,
            'mt5_broker': self.mt5_broker,
            'mt5_balance': self.mt5_balance,
            'mt5_password': self.mt5_password,
            'environment': self.environment,
            'tg_id': self.tg_id,
            'tg_phone': self.tg_phone,
            'tg_session': self.tg_session,
            'tg_channels': self.tg_channels,
            'tg_hash': self.tg_hash,
            'symbol_config': self.symbol_config,
            "dst_channel_gold": -1002404066652,
            "dst_channel_index": -1002535578509
        }