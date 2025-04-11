from telethon.tl.types import PeerChannel
from data.trade import Trade
from data.tg_message import Message
from data.tradeUpdate import TradeUpdate
import logging
import re
from typing import Dict, Any, Optional
from telethon import TelegramClient, events
from data.dbHandler import dbHandler
from business.mt5Handler import MetatraderHandler
from utility.utility_tg import prefilter_message, extract_trade_data, create_trade_entries

logger = logging.getLogger(__name__)

class TelegramAnalyzer:
    def __init__(self, config: Dict[str, Any],db_handler: dbHandler, mt5_handler: MetatraderHandler) -> None:
        """Initialize the Telegram handler."""
        self.config = config
        self.db_handler = db_handler
        self.gold_dst_chat_id = -1002404066652
        self.index_dst_chat_id = -1002535578509
        # Telegram client setup
        self.client = TelegramClient(
            config["tg_session"],
            config["tg_id"],
            config["tg_hash"],
            timeout=10,
            retry_delay=5,
            request_retries=10
        )
        self.mt5_handler = mt5_handler
        self.mt5_handler.initialize_mt5()

        # Register event handlers
        self.client.on(events.NewMessage(chats=config["tg_channels"]))(self.handle_new_message)
        self.client.on(events.MessageEdited(chats=config["tg_channels"]))(self.handle_edited_message)

    async def start(self) -> None:
        """Start the Telegram client."""
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.config["tg_phone"])
            await self.client.sign_in(self.config["tg_phone"], input("Enter the code: "))
        logger.info("✅ Telegram client started!")
        await self.client.run_until_disconnected()

    # Forexeprt free_  -1001187867079

    async def get_all_chats(self) -> None:
        """Retrieve and print all chats."""
        dialogs = await self.client.get_dialogs()
        for dialog in dialogs:
            logger.info(f"Chat Name: {dialog.name}, Chat ID: {dialog.id}")

    async def get_messages_by_id(self,  chat_id: int, limit: int):
        if isinstance(chat_id, int):
            entity = await self.client.get_entity(PeerChannel(chat_id))
        else:
            entity = await self.client.get_entity(chat_id)

        messages = []
        async for message in self.client.iter_messages(entity, limit=limit):
            messages.append(message)

        return messages

    async def handle_new_message(self, event: events.NewMessage.Event) -> None:
        msg_raw_text = event.message.message
        msg_src_chl_name = event.chat.title
        msg_reply_id = event.message.reply_to_msg_id if event.message.is_reply else None
        msg_dst_id = self.config["dst_channel_gold"] if msg_src_chl_name == "Pips Exchange (FX & Gold VIP)" else self.config["dst_channel_index"]

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
        msg_dst_id = self.config["dst_channel_gold"] if msg_src_chl_name == "Pips Exchange (FX & Gold VIP)" else self.config["dst_channel_index"]


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
            trade_results = []
            trades = create_trade_entries(parsed_text, db_message_id, self.config)
            n_trades_to_open = len(trades) if len(trades) > 1 else trades[0]["n_trades"]
            for i in range(0, n_trades_to_open, 1):
                trade = trades[i] if len(trades) > 1 else trades[0]
                trade_id = self.mt5_handler.open_trade(trade)
                if trade_id:
                    trade = Trade(
                        msg_id=int(trade['db_message_id']),
                        order_id=int(trade_id),
                        status='open',
                        break_even=0.0,
                        symbol=trade['symbol'],
                        direction=trade['direction'],
                        volume=trade['lot_size'],
                        stop_loss=trade['SL'],
                        take_profit=trade['TP'],
                        entry_price=trade['entry_price'],
                        account_id=int(trade['account_id'])
                    )
                    trade_results.append(trade)
            if trade_results:
                for trade in trade_results:
                    self.db_handler.insert_trade(trade)
        except Exception as e:
            logger.error(f"❌ Error processing new trade signal: {e}")

    def update_signal_trade_be(self, trades_to_update, parsed_text, text):
        try:
            trades_updated, trade_update_results = [],[]
            for trade in trades_to_update:
                if trade.account_id == self.config["mt5_account_id"]:
                    new_sl = parsed_text['stop_loss'] if parsed_text['stop_loss'] is not None and \
                                                             parsed_text[
                                                                 'stop_loss'] != 0 else None
                    updated_sl = self.mt5_handler.update_trade_break_even(trade.order_id, new_sl)
                    if updated_sl:
                        trade.stop_loss = updated_sl
                        trade.break_even = updated_sl
                        trade_update = TradeUpdate(
                            trade_id=trade.trade_id,
                            order_id=trade.order_id,
                            account_id=trade.account_id,
                            update_action="BE",
                            update_body=text
                        )
                        trade_update_results.append(trade_update)
                else:
                    continue
            if trades_updated:
                for trade in trades_updated:
                    self.db_handler.update_trade(trade)
            self.db_handler.insert_trade_update(trade_update_results)
        except Exception as e:
            logger.error(f"❌ Error updating trade to break even: {e}")

    def close_signal_trade(self, parsed_text, text, trades_to_close):
        logger.info(f'❎ New trade signal to close the position: {parsed_text}')
        try:
            trades_closed, trade_updates_result = [], []
            for trade in trades_to_close:
                if trade.account_id == self.config["mt5_account_id"]:
                    response_close = self.mt5_handler.close_trade(trade.order_id)
                    if response_close:
                        trade.status = 'close'
                        trade_update = TradeUpdate(
                            trade_id=trade.trade_id,
                            order_id=trade.order_id,
                            account_id=trade.account_id,
                            update_action="CLOSE",
                            update_body=text
                        )
                        trade_updates_result.append(trade_update)
                else:
                    continue
            if trades_closed:
                for trade in trades_closed:
                    self.db_handler.update_trade(trade)
            self.db_handler.insert_trade_update(trade_updates_result)
        except Exception as e:
            logger.error(f"❌ Error processing trade close signal: {e}")

    def update_signal_trade(self, existing_trades, parsed_text, db_message_id, text):
        try:
            trades_updated, trade_update_results = [],[]
            trades = create_trade_entries(parsed_text, db_message_id, self.config)
            subset_trades_to_update = [item for item in existing_trades if item.account_id == self.config["mt5_account_id"]]
            for i in range(0, len(subset_trades_to_update), 1):
                trade = subset_trades_to_update[i]
                if trade.account_id == self.config["mt5_account_id"]:
                    new_sl = trades[i]['SL'] if 'SL' in trades[i] and trades[i]['SL'] != 0 else None
                    new_tp = trades[i]['TP'] if 'TP' in trades[i] and trades[i]['TP'] != 0 else None
                    self.mt5_handler.update_trade(trade.order_id, new_sl, new_tp)
                    trade.stop_loss = new_sl
                    trade.take_profit = new_tp
                    trade_update = TradeUpdate(
                        trade_id=trade.trade_id,
                        order_id=trade.order_id,
                        account_id=trade.account_id,
                        update_action="UPDATE",
                        update_body=text
                    )
                    trade_update_results.append(trade_update)
                    trades_updated.append(trade)
                else:
                    continue
            if trades_updated:
                for trade in trades_updated:
                    self.db_handler.update_trade(trade)
            self.db_handler.insert_trade_update(trade_update_results)
        except Exception as e:
            logger.error(f"❌ Error updating signal trade: {e}")