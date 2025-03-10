from model.trades import Trade
from model.messages import Message
from model.trade_updates import TradeUpdate
import logging
import re
from typing import Dict, Any, Optional
from telethon import TelegramClient, events

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
        if not self.prefilter_message(text):
            logger.error(f"❌ Invalid message: {text}")
            return
        await self.client.forward_messages(self.destination_chat_id, event.message)
        message = Message(telegram_id=event.message.id, chat_id=event.chat_id, timestamp=event.message.date, text=text, processed=False)
        parsed_text = self.extract_trade_data(text)

        if parsed_text['message_type'] == 'create':
            logger.info(f'🆕 New trade signal to open a new position: {parsed_text}')
            try:
                db_message_id = self.dbHandler.insert_message(message)
                trades = self.create_trade_dicts(parsed_text, db_message_id)
                trade_results = self.metatraderHandler.open_multiple_trades(trades, self.config[self.mt_key_based_on_env]['TRADE_MANAGEMENT'][parsed_text['symbol']]['default_trades'])
                for trade in trade_results:
                    self.dbHandler.insert_trade(trade)
                message.processed = True
                self.dbHandler.update_message(message)
            except Exception as e:
                logger.error(f"❌ Error processing new trade signal: {e}")
        elif parsed_text['message_type'] == 'update':
            logger.info(f'📝 New trade signal to put the position in break even: {parsed_text}')
            try:
                if reply_to_id is None:
                    trades_to_update = self.dbHandler.get_latest_message_with_trades()
                    for item in trades_to_update:
                        sl = parsed_text['stop_loss'] if parsed_text['stop_loss'] is not None and parsed_text['stop_loss'] != 0 else None
                        response_be = self.metatraderHandler.update_trade_break_even(item.order_id, sl)
                        if response_be is not None:
                            trade_updates = TradeUpdate(item.id, str(text), response_be, str(item.order_id))
                            self.dbHandler.insert_trade_update(trade_updates)
                            item.stop_loss = response_be
                            item.break_even = response_be
                            self.dbHandler.update_trade(item)
                else:
                    replied_message = self.dbHandler.get_message_by_id(reply_to_id, event.chat_id)
                    trades_to_update = self.dbHandler.get_trades_by_id(replied_message.id)
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
            except Exception as e:
                logger.error(f"❌ Error processing trade update signal: {e}")
        elif parsed_text['message_type'] == 'close':
            logger.info(f'❎ New trade signal to close the position: {parsed_text}')
            try:
                trades_to_close = self.dbHandler.get_latest_message_with_trades()
                for item in trades_to_close:
                    response_close = self.metatraderHandler.close_trade(item.order_id)
                    if response_close:
                        item.status = 'close'
                        self.dbHandler.update_trade(item)
                        trade_updates = TradeUpdate(item.id, str(text), -1, str(item.order_id))
                        self.dbHandler.insert_trade_update(trade_updates)
            except Exception as e:
                logger.error(f"❌ Error processing trade close signal: {e}")
        else:
            logger.error(f"❌ Invalid message type, not supported: {parsed_text}")

    async def handle_edited_message(self, event: events.NewMessage.Event) -> None:
        """Handle edited messages from Telegram."""
        edited_text = event.message.message
        if not self.prefilter_message(edited_text):
            logger.error(f"❌ Invalid message: {edited_text}")
            return
        await self.client.forward_messages(self.destination_chat_id, event.message)
        try:
            existing_message = self.dbHandler.get_message_by_id(event.message.id, event.chat_id)
            message = Message(telegram_id=event.message.id, chat_id=event.chat_id, timestamp=event.message.date, text=edited_text, processed=False)
            parsed_text = self.extract_trade_data(edited_text)

            if parsed_text['message_type'] == 'create':
                existing_trades = self.dbHandler.get_trades_by_id(existing_message.id)
                trades = self.create_trade_dicts(parsed_text, existing_message.id)[-len(existing_trades):]
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
            else:
                logger.error(f"❌ Invalid message type: {parsed_text}")
        except Exception as e:
            logger.error(f"❌ Error processing edited message: {e}")

    def prefilter_message(self, message: str) -> bool:
        """Prefilter the message to remove unwanted characters."""
        try:
            # Regex patterns to match valid messages
            trade_pattern = re.compile(r'\b[A-Z0-9]+\s+(BUY|SELL|BUY LIMIT|BUY STOP|SELL LIMIT|SELL STOP)\s*@?\s*[0-9\.]+', re.IGNORECASE)
            sl_tp_pattern = re.compile(r'\bSL[-:]\s*[0-9\.]+|TP[0-9]+[-:]\s*[0-9\.]+', re.IGNORECASE)
            update_keywords = ["Move SL at BE","Move SL to BE", "Move SL","Updated", "Update full position", "Close early", "reduce risk", "Close", "Close all", "Close trade"]
            update_keywords_sl = r'\b(?:SL\s*[0-9]+\s*reduce risk|All SL \d+|[A-Za-z]{3,6}\s*SL\s*@\s*\d+)\b'

            # Check if the message is a trade signal
            if trade_pattern.search(message) or any(keyword.lower() in message.lower() for keyword in update_keywords) or re.search(update_keywords_sl, message, re.IGNORECASE):
                logger.info(f"📨 Valid message received!: {message}")
                return True
            # Check if the message is a SL/TP pattern
            elif sl_tp_pattern.search(message):
                logger.info(f"📨 Valid message received!: {message}")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"❌ Error in prefiltering message: {e}")
            return False

    def extract_trade_data(self, message: str) -> Optional[Dict[str, Any]]:
        """Extract trade data from the message."""
        patterns = {
            'symbol': r'(?P<symbol>[A-Za-z0-9]+)\s+(?P<direction>BUY|SELL|BUY LIMIT|BUY STOP|SELL LIMIT|SELL STOP)\s*@?\s*(?P<entry_price>\d+\.?\d*)',
            'stop_loss': r'(?:SL|stoploss|sl)\s*-?\s*(\d+\.?\d*)',
            'take_profits': r'TP\d+\s*[-:]\s*(\d+\.?\d*)',
            'break_even': r'\b(?:BE|Break Even|Risk Free|Move SL at BE|Move stop loss at BE|Move stop loss at break even|Updated|Update full position|SL\s*[0-9]+\s*reduce risk|All SL \d+|[A-Za-z]{3,6}\s*SL\s*@\s*\d+)\b',
            'close_before': r'\b(?:Close early|Close|Close all|Close trade)\b'
        }
        try:
            break_even_match = re.search(patterns['break_even'], message, re.IGNORECASE)
            close_before_match = re.search(patterns['close_before'], message, re.IGNORECASE)
            trade_info = {}
            if break_even_match:
                trade_info['break_even'] = True
                trade_info['message_type'] = 'update'
                # Capture the stop loss value from the matched group
                parts = break_even_match.group(0).split()
                if parts:
                    trade_info['symbol'] = str(parts[0]).upper() if re.match(r'^[A-Z]{3,6}$', parts[0]) else None
                    trade_info['stop_loss'] = float(parts[-1]) if parts[-1].replace('.', '', 1).isdigit() else 0

                return trade_info

            if close_before_match:
                trade_info['close_before'] = True
                trade_info['message_type'] = 'close'

                return trade_info

            trade_info = {
                'symbol': None,
                'direction': None,
                'entry_price': 0,
                'stop_loss': 0,
                'take_profits': [],
                'message_type': None
            }

            # Extract main data (symbol, direction, entry price)
            main_match = re.search(patterns['symbol'], message, re.IGNORECASE)
            if main_match:
                trade_info['symbol'] = main_match.group('symbol').upper()
                trade_info['direction'] = main_match.group('direction').upper()
                trade_info['entry_price'] = float(main_match.group('entry_price'))
                trade_info['message_type'] = 'create'

            # Extract stop loss
            sl_match = re.search(patterns['stop_loss'], message, re.IGNORECASE)
            if sl_match:
                trade_info['stop_loss'] = float(sl_match.group(1))

            # Extract take profits
            tp_matches = re.findall(patterns['take_profits'], message, re.IGNORECASE)
            if tp_matches:
                trade_info['take_profits'] = [float(tp) for tp in tp_matches]

            if all(value in [None, []] for value in trade_info.values()):
                return None

            logger.info(f"📨 Parsed text: {trade_info}")

            return trade_info
        except Exception as e:
            logger.error(f"❌ Error extracting trade data: {e}")
            return None

    def create_trade_dicts(self, trade_dict, message_id):
        """Create trade dictionaries from parsed trade data."""
        try:
            tps = trade_dict.get('take_profits', {})
            symbol_config = self.config[self.mt_key_based_on_env]['TRADE_MANAGEMENT'][trade_dict['symbol'].upper()]

            # Ensure tps is a list (if not, initialize as empty)
            if not isinstance(tps, list) or not tps:
                tps = []

            tp_length = len(tps)
            trade_dicts = []

            # If there's only one TP and it's None, create a basic trade dict
            if tp_length == 0:
                new_trade_dict = {
                    'symbol': symbol_config['symbol'],
                    'direction': trade_dict['direction'],
                    'entry_price': trade_dict['entry_price'],
                    'volume': symbol_config['default_lot_size'],
                    'db_message_id': message_id,
                    'SL': trade_dict.get('stop_loss', '0'),
                    'TP': '0'
                }
                trade_dicts.append(new_trade_dict)
            else:
                # Determine how many TPs to use based on the length of the tps array
                if tp_length < 6:
                    selected_tps = tps[-2:]  # Last 2 take profits
                else:
                    selected_tps = tps[-3:]  # Last 3 take profits

                # Create trade dicts for each selected take profit
                for tp in selected_tps:
                    new_trade_dict = {
                        'symbol': symbol_config['symbol'],
                        'direction': trade_dict['direction'],
                        'entry_price': trade_dict['entry_price'],
                        'volume': symbol_config['default_lot_size'],
                        'db_message_id': message_id,
                        'SL': trade_dict.get('stop_loss', '0'),
                        'TP': tp if tp is not None else '0'
                    }
                    trade_dicts.append(new_trade_dict)

            return trade_dicts
        except Exception as e:
            logger.error(f"❌ Error creating trade dictionaries: {e}")
            return []