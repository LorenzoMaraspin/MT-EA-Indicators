class SoftwareAccounts():
    def __init__(self,
                 mt5_account_id: int,
                 mt5_server: str,
                 mt5_broker: str,
                 mt5_balance: int,
                 mt5_password: str,
                 environment: str,
                 telegram_id: str,
                 telegram_phone: str,
                 telegram_session: str,
                 telegram_channels: str,
                 telegram_hash: str):
        self.mt5_account_id = mt5_account_id
        self.mt5_server = mt5_server
        self.mt5_broker = mt5_broker
        self.mt5_balance = mt5_balance
        self.mt5_password = mt5_password
        self.environment = environment
        self.telegram_id = telegram_id
        self.telegram_phone = telegram_phone
        self.telegram_session = telegram_session
        self.telegram_channels = telegram_channels
        self.telegram_hash = telegram_hash

    def to_dict(self):
        return {
            'mt5_account_id': self.mt5_account_id,
            'mt5_server': self.mt5_server,
            'mt5_broker': self.mt5_broker,
            'mt5_balance': self.mt5_balance,
            'mt5_password': self.mt5_password,
            'environment': self.environment,
            'telegram_id': self.telegram_id,
            'telegram_phone': self.telegram_phone,
            'telegram_session': self.telegram_session,
            'telegram_channels': self.telegram_channels,
            'telegram_hash': self.telegram_hash
        }