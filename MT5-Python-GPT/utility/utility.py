import logging
import os
import re
from collections import defaultdict
from typing import Dict, Any, Optional
from model.trade_updates import TradeUpdate

logger = logging.getLogger(__name__)

def read_file(file_path: str) -> str:
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError as e_f:
        logger.exception(f"Error: File not found: {e_f}")
        raise e_f
    except IOError as e_io:
        logger.exception(f"Error: An I/O error occurred: {e_io}")
        raise e_io

def read_env_vars():
    config = {}
    config['MT5'] = {
        'ACCOUNT': int(os.environ.get('MT5_ACCOUNT')),
        'PASSWORD': os.environ.get('MT5_PASSWORD').strip(),
        'SERVER': os.environ.get('MT5_SERVER').strip(),
        'TRADE_MANAGEMENT': {
            'US30': {
                "symbol": "US30.cash",
                "default_trades": 3,
                "default_lot_size": 2.0
            },
            'XAUUSD': {
                "symbol": "XAUUSD",
                "default_trades": 2,
                "default_lot_size": 0.5
            },
            'XAU': {
                "symbol": "XAUUSD",
                "default_trades": 2,
                "default_lot_size": 0.5
            }
        }
    }

    config['MT5_DEV'] = {
        'ACCOUNT': int(os.environ.get('MT5_ACCOUNT_DEV')),
        'PASSWORD': os.environ.get('MT5_PASSWORD_DEV').strip(),
        'SERVER': os.environ.get('MT5_SERVER_DEV').strip(),
        'TRADE_MANAGEMENT': {
            'US30': {
                "symbol": "DJ30",
                "default_trades": 3,
                "default_lot_size": 2.0
            },
            'XAUUSD': {
                "symbol": "XAUUSD+",
                "default_trades": 2,
                "default_lot_size": 0.5
            },
            'XAU': {
                "symbol": "XAUUSD+",
                "default_trades": 2,
                "default_lot_size": 0.5
            }
        }
    }

    config['TG_PROD'] = {
        'ID': os.environ.get('TELEGRAM_M_API_ID'),
        'HASH': os.environ.get('TELEGRAM_M_API_HASH'),
        'PHONE': os.environ.get('TELEGRAM_M_PHONE'),
        'SESSION': os.environ.get('TELEGRAM_M_SESSION'),
        'CHANNELS': [int(channel) for channel in os.environ.get('TELEGRAM_M_CHANNELS').split(',')]
    }
    config['TG_DEV'] = {
        'ID': os.environ.get('TELEGRAM_API_ID'),
        'HASH': os.environ.get('TELEGRAM_API_HASH'),
        'PHONE': os.environ.get('TELEGRAM_PHONE'),
        'SESSION': os.environ.get('TELEGRAM_SESSION'),
        'CHANNELS': [int(channel) for channel in os.environ.get('TELEGRAM_CHANNELS').split(',')]
    }

    config['DB'] = {
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
        'DBNAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PWD')
    }
    config['DB_DEV'] = {
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
        'DBNAME': os.environ.get('DB_NAME_DEV'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PWD')
    }

    config['ENV'] = os.environ.get('ENVIRONMENT')
    config['LLAMA_API_KEY'] = os.environ.get('LLAMA_AI_KEY')

    return config

def compare_trades_still_open(db, metatrader):
    all_running_trades = metatrader.get_all_position()
    all_db_trades = db.get_all_trades()

    if not all_db_trades and not all_running_trades:
        return
    if not all_db_trades:
        return

    all_db_trades_by_message_id = defaultdict(list)
    for trade in all_db_trades:
        all_db_trades_by_message_id[trade.message_id].append(trade)

    found_ids = []
    not_found_ids = []

    # Check each ID in the first array
    for key, value in all_db_trades_by_message_id.items():
        for trade in value:
            if int(trade.order_id) in all_running_trades:
                found_ids.append(trade)
            else:
                not_found_ids.append(trade)
        if len(value) == len(found_ids):
            return
            #logger.info("☑️ No further action needed")
        elif len(found_ids) == 0 and len(value) == len(not_found_ids):
            logger.info("©️ All trade record in open state are closed in MT, update all trade records")
            for trade_to_close in not_found_ids:
                trade_to_close.status = 'close'
                db.update_trade(trade_to_close)
        elif len(not_found_ids) != 0:
            logger.info("🔄 Update the stoploss of the remaining open trades")
            for trade_to_close in not_found_ids:
                trade_to_close.status = 'close'
                db.update_trade(trade_to_close)

            for trade_to_update in found_ids:
                new_sl = metatrader.update_trade_break_even(trade_to_update.order_id, None)
                trade_to_update.stop_loss = new_sl
                trade_to_update.break_even = new_sl
                db.update_trade(trade_to_update)
                trade_updates = TradeUpdate(trade_to_update.id, "Move to BE, after first TP", 1, str(trade_to_update.order_id))
                db.insert_trade_update(trade_updates)

def prefilter_message(message: str) -> bool:
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

def extract_trade_data(message: str) -> Optional[Dict[str, Any]]:
    """Extract trade data from the message."""
    patterns = {
        'symbol': r'(?P<symbol>[A-Za-z0-9]+)\s+(?P<direction>BUY|SELL|BUY LIMIT|BUY STOP|SELL LIMIT|SELL STOP)\s*@?\s*(?P<entry_price>\d+\.?\d*)',
        'stop_loss': r'(?:SL|stoploss|sl)\s*-?\s*(\d+\.?\d*)',
        'take_profits': r'TP\d+\s*[-:]\s*(\d+\.?\d*)',
        'break_even': r'\b(?:BE|Break Even|Risk Free|Move SL at BE|Move stop loss at BE|Move stop loss at break even|Updated|Update full position|SL\s*[0-9]+\s*reduce risk|All SL \d+|[A-Za-z]{3,6}\s*SL\s*@\s*\d+|Tighten SL\s*(\d+(?:\.\d+)?)\s*,\s*Reduce Risk)\b',
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
                number_index =  next((i for i, item in enumerate(parts) if any(char.isdigit() for char in item)), None)
                if number_index is not None:
                    trade_info['stop_loss'] = parts[number_index]
                else:
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

def create_trade_dicts(trade_dict, message_id, config, mt_key):
    """Create trade dictionaries from parsed trade data."""
    try:
        tps = trade_dict.get('take_profits', {})
        symbol_config = config[mt_key]['TRADE_MANAGEMENT'][trade_dict['symbol'].upper()]

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

