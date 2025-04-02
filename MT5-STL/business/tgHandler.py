from data.trade import Trade
from data.tg_message import Message
from data.tradeUpdate import TradeUpdate
import logging
import re
from typing import Dict, Any, Optional
from telethon import TelegramClient, events
from utility.utility_mt5 import open_trades_multi_account, update_trades_be_multi_account, close_trades_multi_account, update_trades_multi_account
from utility.utility_tg import prefilter_message, extract_trade_data, create_trade_entries

logger = logging.getLogger(__name__)

class TelegramAnalyzer:
    def __init__(self, config: Dict[str, Any],db_handler):
        """Initialize the Telegram handler."""
        self.config = config
        self.db_handler = db_handler
        self.gold_dst_chat_id = -1002404066652
        self.index_dst_chat_id = -1002535578509
        # Telegram client setup
        self.client = TelegramClient(
            config["TG"]['SESSION'],
            config["TG"]['ID'],
            config["TG"]['HASH'],
            timeout=10,
            retry_delay=5,
            request_retries=10
        )

        # Register event handlers
        self.client.on(events.NewMessage(chats=config["TG"]['CHANNELS']))(self.handle_new_message)
        self.client.on(events.MessageEdited(chats=config["TG"]['CHANNELS']))(self.handle_edited_message)

    async def start(self) -> None:
        """Start the Telegram client."""
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.config["TG"]['PHONE'])
            await self.client.sign_in(self.config["TG"]['PHONE'], input("Enter the code: "))
        logger.info("✅ Telegram client started!")
        await self.client.run_until_disconnected()

    async def get_all_chats(self) -> None:
        """Retrieve and print all chats."""
        dialogs = await self.client.get_dialogs()
        for dialog in dialogs:
            logger.info(f"Chat Name: {dialog.name}, Chat ID: {dialog.id}")

    async def handle_new_message(self, event: events.NewMessage.Event) -> None:
        msg_raw_text = event.message.message
        msg_src_chl_name = event.chat.title
        msg_reply_id = event.message.reply_to_msg_id if event.message.is_reply else None
        msg_dst_id = self.config["TG"]["DST_CHANNEL_GOLD"] if msg_src_chl_name == "Pips Exchange (FX & Gold VIP)" else self.config["TG"]["DST_CHANNEL_INDEX"]

        if not prefilter_message(msg_raw_text):
            logger.error(f"❌ Invalid message: {msg_raw_text}")
            return

        forwarded_message = await self.client.forward_messages(msg_dst_id, event.message)

        db_message = Message(
            tg_msg_id=event.message.id,
            tg_chat_id=event.chat_id,
            tg_src_chat_name=msg_src_chl_name,
            tg_dst_msg_id=int(forwarded_message.id),
            tg_dst_chat_id=msg_dst_id,
            msg_body=msg_raw_text,
            msg_status="new",
            msg_timestamp=event.message.date
        )

        msg_parsed_text = extract_trade_data(msg_raw_text)
        if msg_parsed_text['message_type'] == 'create':
            self.create_new_signal_trade(msg_parsed_text, db_message)
        elif msg_parsed_text['message_type'] == 'update':
            logger.info(f'📝 New trade signal to put the position in break even: {msg_parsed_text}')
            if msg_reply_id:
                replied_message = self.db_handler.get_message_by_id(msg_reply_id, event.chat_id)
                trades_to_update = self.db_handler.get_trades_by_id(replied_message.msg_id)
            else:
                trades_to_update = self.db_handler.get_open_trades_based_on_src_tg_chat(tg_src_chat_name=msg_src_chl_name)
            trade_update_response = self.update_signal_trade_be(trades_to_update, msg_parsed_text, msg_raw_text)
            if trade_update_response:
                self.db_handler.insert_trade_update(trade_update_response)
        elif msg_parsed_text['message_type']  == 'close':
            if msg_reply_id:
                replied_message = self.db_handler.get_message_by_id(msg_reply_id, event.chat_id)
                trades_to_close = self.db_handler.get_trades_by_id(replied_message.msg_id)
            else:
                trades_to_close = self.db_handler.get_open_trades_based_on_src_tg_chat(tg_src_chat_name=msg_src_chl_name)
            self.close_signal_trade(msg_parsed_text, msg_raw_text, trades_to_close)
    async def handle_edited_message(self, event: events.NewMessage.Event) -> None:
        msg_raw_edited_text = event.message.message
        msg_src_chl_name = event.chat.title
        msg_dst_id = self.config["TG"]["DST_CHANNEL_GOLD"] if msg_src_chl_name == "Pips Exchange (FX & Gold VIP)" else \
        self.config["TG"]["DST_CHANNEL_INDEX"]

        forwarded_message = await self.client.forward_messages(msg_dst_id, event.message)
        existing_message = self.db_handler.get_message_by_id(event.message.id, event.chat_id)

        msg_parsed_edited_text = extract_trade_data(msg_raw_edited_text)
        if msg_parsed_edited_text['message_type'] == 'create':
            existing_trades = self.db_handler.get_trades_by_id(existing_message.msg_id)
            self.update_signal_trade(existing_trades, msg_parsed_edited_text, existing_message.msg_id, msg_raw_edited_text)
            existing_message.msg_status = "updated"
            existing_message.msg_body = msg_raw_edited_text
            self.db_handler.update_message(existing_message)

    def create_new_signal_trade(self, parsed_text, message):
        logger.info(f'🆕 New trade signal to open a new position: {parsed_text}')
        try:
            db_message_id = self.db_handler.insert_message(message)
            trade_results = open_trades_multi_account(parsed_text, self.config, db_message_id)
            if trade_results:
                for trade in trade_results:
                    self.db_handler.insert_trade(trade)
        except Exception as e:
            logger.error(f"❌ Error processing new trade signal: {e}")

    def update_signal_trade_be(self, trades_to_update, parsed_text, text):
        try:
            trades_updated, trade_update_results = update_trades_be_multi_account(trades_to_update, self.config, parsed_text, text)
            if trades_updated:
                for trade in trades_updated:
                    self.db_handler.update_trade(trade)
            self.db_handler.insert_trade_update(trade_update_results)
        except Exception as e:
            logger.error(f"❌ Error updating trade to break even: {e}")

    def close_signal_trade(self, parsed_text, text, trades_to_close):
        logger.info(f'❎ New trade signal to close the position: {parsed_text}')
        try:
            trades_closed, trade_update_results = close_trades_multi_account(trades_to_close, self.config, text)
            if trades_closed:
                for trade in trades_closed:
                    self.db_handler.update_trade(trade)
            self.db_handler.insert_trade_update(trade_update_results)
        except Exception as e:
            logger.error(f"❌ Error processing trade close signal: {e}")

    def update_signal_trade(self, existing_trades, parsed_text, db_message_id, text):
        try:
            trades_updated, trade_update_results = update_trades_multi_account(existing_trades, self.config, parsed_text, db_message_id, text)
            if trades_updated:
                for trade in trades_updated:
                    self.db_handler.update_trade(trade)
            self.db_handler.insert_trade_update(trade_update_results)
        except Exception as e:
            logger.error(f"❌ Error updating signal trade: {e}")