class Message():
    def __init__(self, telegram_id: int, chat_id: int, timestamp: str, text: str, processed: bool):
        self.telegram_id = telegram_id
        self.chat_id = chat_id
        self.timestamp = timestamp
        self.text = text
        self.processed = processed