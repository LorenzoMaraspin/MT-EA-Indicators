class Message():
    def __init__(
            self,
            tg_msg_id: int,
            tg_chat_id: str,
            tg_src_chat_name: str,
            tg_dst_chat_id: str,
            tg_dst_msg_id: int,
            msg_body: str,
            msg_timestamp: str,
            msg_status: str,
            msg_id: int = None):
        self.msg_id = msg_id
        self.tg_msg_id = tg_msg_id
        self.tg_chat_id = str(tg_chat_id)
        self.tg_src_chat_name = tg_src_chat_name
        self.tg_dst_chat_id = str(tg_dst_chat_id)
        self.tg_dst_msg_id = tg_dst_msg_id
        self.msg_timestamp = msg_timestamp
        self.msg_body = msg_body
        self.msg_status = msg_status

    def to_dict(self):
        return {
            'tg_msg_id': self.tg_msg_id,
            'tg_chat_id': self.tg_chat_id,
            'tg_src_chat_name': self.tg_src_chat_name,
            'tg_dst_chat_id': self.tg_dst_chat_id,
            'tg_dst_msg_id': self.tg_dst_msg_id,
            'msg_timestamp': self.msg_timestamp,
            'msg_body': self.msg_body,
            'msg_status': self.msg_status
        }