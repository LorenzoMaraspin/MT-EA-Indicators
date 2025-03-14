from model.trades import Trade
from model.messages import Message
from model.trade_updates import TradeUpdate
import logging
import re
from typing import Dict, Any, Optional
from telethon import TelegramClient, events
from utility.utility import prefilter_message, extract_trade_data, create_trade_dicts

logger = logging.getLogger(__name__)

class TelegramAnalyzer:
    def __init__(self, config: Dict[str, Any], metatraderHandler=None, dbHandler=None):
        """Initialize the Telegram handler."""
        self.config = config
        self.metatraderHandler = metatraderHandler
        self.dbHandler = dbHandler
        self.destination_chat_id = -1002404066652

        # Telegram client setup
        self.tg_key_based_on_env = "TG_DEV" if config['ENV'] == 'DEV' else "TG_PROD"
        self.mt_key_based_on_env = "MT5_DEV" if config['ENV'] == 'DEV' else "MT5"
        self.client = TelegramClient(
            config[self.tg_key_based_on_env]['SESSION'],
            config[self.tg_key_based_on_env]['ID'],
            config[self.tg_key_based_on_env]['HASH'],
            timeout=10,
            retry_delay=5,
            request_retries=10
        )

        # Register event handlers
        self.client.on(events.NewMessage(chats=config[self.tg_key_based_on_env]['CHANNELS']))(self.handle_new_message)
        self.client.on(events.MessageEdited(chats=config[self.tg_key_based_on_env]['CHANNELS']))(self.handle_edited_message)

    async def start(self) -> None:
        """Start the Telegram client."""
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.config[self.tg_key_based_on_env]['PHONE'])
            await self.client.sign_in(self.config[self.tg_key_based_on_env]['PHONE'], input("Enter the code: "))
        logger.info("✅ Telegram client started!")
        await self.client.run_until_disconnected()

    async def handle_new_message(self, event: events.NewMessage.Event) -> None:
        """Handle new messages from Telegram."""
        text = event.message.message
        reply_to_id = event.message.reply_to_msg_id if event.message.is_reply else None
        if not prefilter_message(text):
            logger.error(f"❌ Invalid message: {text}")
            return
        if self.config['ENV'] == 'PROD':
            await self.client.forward_messages(self.destination_chat_id, event.message)
        message = Message(telegram_id=event.message.id, chat_id=event.chat_id, timestamp=event.message.date, text=text, processed=False)
        parsed_text = extract_trade_data(text)

        if parsed_text['message_type'] == 'create':
            self.create_new_signal_trade(parsed_text, message)
        elif parsed_text['message_type'] == 'update':
            logger.info(f'📝 New trade signal to put the position in break even: {parsed_text}')
            try:
                if reply_to_id is None:
                    trades_to_update = self.dbHandler.get_latest_message_with_trades()
                else:
                    replied_message = self.dbHandler.get_message_by_id(reply_to_id, event.chat_id)
                    trades_to_update = self.dbHandler.get_trades_by_id(replied_message.id)
                self.update_signal_trade(trades_to_update, parsed_text, text)
            except Exception as e:
                logger.error(f"❌ Error processing trade update signal: {e}")
        elif parsed_text['message_type'] == 'close':
            if reply_to_id is None:
                trades_to_close = self.dbHandler.get_latest_message_with_trades()
            else:
                replied_message = self.dbHandler.get_message_by_id(reply_to_id, event.chat_id)
                trades_to_close = self.dbHandler.get_trades_by_id(replied_message.id)
            self.close_signal_trade(parsed_text, text, trades_to_close)
        else:
            logger.error(f"❌ Invalid message type, not supported: {parsed_text}")

    async def handle_edited_message(self, event: events.NewMessage.Event) -> None:
        """Handle edited messages from Telegram."""
        edited_text = event.message.message
        if not prefilter_message(edited_text):
            logger.error(f"❌ Invalid message: {edited_text}")
            return
        if self.config['ENV'] == 'PROD':
            await self.client.forward_messages(self.destination_chat_id, event.message)
        try:
            existing_message = self.dbHandler.get_message_by_id(event.message.id, event.chat_id)
            message = Message(telegram_id=event.message.id, chat_id=event.chat_id, timestamp=event.message.date, text=edited_text, processed=False)
            parsed_text = extract_trade_data(edited_text)

            if parsed_text['message_type'] == 'create' and existing_message is not None:
                existing_trades = self.dbHandler.get_trades_by_id(existing_message.id)
                trades = create_trade_dicts(parsed_text, existing_message.id,self.config, self.mt_key_based_on_env)[-len(existing_trades):]
                for i in range(len(existing_trades)):
                    element = existing_trades[i]
                    if len(trades) < len(existing_trades):
                        element.stop_loss = trades[0]['SL']
                        element.take_profit = trades[0]['TP']
                    else:
                        element.stop_loss = trades[i]['SL']
                        element.take_profit = trades[i]['TP']
                    self.metatraderHandler.update_trade(element.order_id, element.stop_loss, element.take_profit)
                    self.dbHandler.update_trade(element)
                    message.processed = True
                    self.dbHandler.update_message(message)
                    trade_updates = TradeUpdate(element.id, str(edited_text), 1, str(element.order_id))
                    self.dbHandler.insert_trade_update(trade_updates)
            elif parsed_text['message_type'] == 'create' and existing_message is None:
                self.create_new_signal_trade(parsed_text, message)
            else:
                logger.error(f"❌ Invalid message type: {parsed_text}")
        except Exception as e:
            logger.error(f"❌ Error processing edited message: {e}")

    def create_new_signal_trade(self, parsed_text, message):
        logger.info(f'🆕 New trade signal to open a new position: {parsed_text}')
        try:
            db_message_id = self.dbHandler.insert_message(message)
            trades = create_trade_dicts(parsed_text, db_message_id, self.config, self.mt_key_based_on_env)
            trade_results = self.metatraderHandler.open_multiple_trades(trades, self.config[self.mt_key_based_on_env][
                'TRADE_MANAGEMENT'][parsed_text['symbol']]['default_trades'])
            if trade_results:
                for trade in trade_results:
                    self.dbHandler.insert_trade(trade)
                message.processed = True
                self.dbHandler.update_message(message)
        except Exception as e:
            logger.error(f"❌ Error processing new trade signal: {e}")

    def close_signal_trade(self, parsed_text, text, trades_to_close):
        logger.info(f'❎ New trade signal to close the position: {parsed_text}')
        try:
            for item in trades_to_close:
                response_close = self.metatraderHandler.close_trade(item.order_id)
                if response_close:
                    item.status = 'close'
                    self.dbHandler.update_trade(item)
                    trade_updates = TradeUpdate(item.id, str(text), -1, str(item.order_id))
                    self.dbHandler.insert_trade_update(trade_updates)
        except Exception as e:
            logger.error(f"❌ Error processing trade close signal: {e}")

    def update_signal_trade(self, trades_to_update, parsed_text, text):
        for item in trades_to_update:
            sl = parsed_text['stop_loss'] if parsed_text['stop_loss'] is not None and parsed_text[
                'stop_loss'] != 0 else None
            response_be = self.metatraderHandler.update_trade_break_even(item.order_id, sl)
            if response_be is not None:
                trade_updates = TradeUpdate(item.id, str(text), response_be, str(item.order_id))
                self.dbHandler.insert_trade_update(trade_updates)
                item.stop_loss = response_be
                item.break_even = response_be
                self.dbHandler.update_trade(item)