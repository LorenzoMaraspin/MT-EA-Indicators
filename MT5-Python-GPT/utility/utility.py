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

def generate_broker_config(symbol, default_trades, lot_sizes, account):
    lot_size = lot_sizes[0] if account.mt5_balance == 100000 else lot_sizes[1]

    return {
        "symbol": symbol,
        "default_trades": default_trades,
        "default_lot_size": lot_size
    }

def read_env_vars():
    config = {}
    config['ENV'] = os.environ.get('ENVIRONMENT')

    config['DB'] = {
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
        'DBNAME': os.environ.get('DB_NAME') if config['ENV'] == 'PROD' else os.environ.get('DB_NAME_DEV'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PWD')
    }

    return config

def update_config_with_accounts(account, config):
    config['BROKER'] = {
        'ftmo': {
            'US30': generate_broker_config("US30.cash", 3, [2.0, 0.15], account),
            'XAUUSD': generate_broker_config("XAUUSD", 2, [0.5, 0.04], account),
            'XAU': generate_broker_config("XAUUSD", 2, [0.5, 0.04], account),
            'EURUSD': generate_broker_config("EURUSD", 2, [0.7, 0.06], account)
        },
        'vantage': {
            'US30': generate_broker_config("DJ30", 3, [2.0, 0.15], account),
            'XAUUSD': generate_broker_config("XAUUSD+", 2, [0.5, 0.04], account),
            'XAU': generate_broker_config("XAUUSD+", 2, [0.5, 0.04], account),
            'EURUSD': generate_broker_config("EURUSD+", 2, [0.7, 0.06], account)
        },
        'fundingpips': {
            'US30': generate_broker_config("DJI30", 3, [2.0, 0.02], account),
            'XAUUSD': generate_broker_config("XAUUSD", 2, [0.5, 0.04], account),
            'XAU': generate_broker_config("XAUUSD", 2, [0.5, 0.04], account),
            'EURUSD': generate_broker_config("EURUSD", 2, [0.7, 0.06], account)
        }
    }

    config['MT5'] = {
        'ACCOUNT': int(account.mt5_account_id),
        'PASSWORD': account.mt5_password,
        'SERVER': account.mt5_server,
        'BROKER': account.mt5_broker,
        'TRADE_MANAGEMENT': config['BROKER'][account.mt5_broker.lower()]
    }
    config['TG'] = {
        'ID': account.telegram_id,
        'HASH': account.telegram_hash,
        'PHONE': account.telegram_phone,
        'SESSION': account.telegram_session,
        'CHANNELS': [int(channel) for channel in account.telegram_channels.split(',')]
    }

    return config

def compare_trades_still_open(db, metatrader):
    all_running_trades = metatrader.get_all_position()
    all_db_trades = db.get_all_trades(metatrader.account)

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
                trade_updates = TradeUpdate(trade_to_update.id, "Move to BE, after first TP", 1, str(trade_to_update.order_id), metatrader.account)
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
                'db_message_id': message_id,
                'SL': trade_dict.get('stop_loss', '0'),
                'TP': '0',
                'account_id': trade_dict['account_id']
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
                    'db_message_id': message_id,
                    'SL': trade_dict.get('stop_loss', '0'),
                    'TP': tp if tp is not None else '0',
                    'account_id': trade_dict['account_id']
                }
                trade_dicts.append(new_trade_dict)

        return trade_dicts
    except Exception as e:
        logger.error(f"❌ Error creating trade dictionaries: {e}")
        return []

