class Message():
    def __init__(self, telegram_id: int, chat_id: str, timestamp: str, text: str, processed: bool, id: int = None):
        self.id = id
        self.telegram_id = telegram_id
        self.chat_id = chat_id
        self.timestamp = timestamp
        self.text = text
        self.processed = processed

    def to_dict(self):
        return {
            'telegram_id': self.telegram_id,
            'chat_id': str(self.chat_id),
            'timestamp': self.timestamp,
            'text': self.text,
            'processed': self.processed
        }