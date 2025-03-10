import logging
import os
from collections import defaultdict

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

    config['ENV'] = os.environ.get('ENVIRONMENT')
    config['LLAMA_API_KEY'] = os.environ.get('LLAMA_AI_KEY')

    return config

def compare_trades_still_open(db, metatrader):
    all_running_trades = metatrader.get_all_position()
    all_db_trades = db.get_all_trades()
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
            logger.info("No further action needed")
        elif len(found_ids) == 0 and len(value) == len(not_found_ids):
            logger.info("All trade record in open state are closed in MT, update all trade records")
            for trade_to_close in not_found_ids:
                trade_to_close.status = 'close'
                db.update_trade(trade_to_close)
        elif len(not_found_ids) != 0:
            logger.info("Update the stoploss of the remaining open trades")
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


