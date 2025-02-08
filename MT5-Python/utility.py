import os
import logging
import re

logger = logging.getLogger(__name__)

def read_env_vars():
    config = {}
    config['MT5'] = {
        'ACCOUNT': int(os.environ.get('MT5_ACCOUNT')),
        'PASSWORD': os.environ.get('MT5_PASSWORD').strip(),
        'SERVER': os.environ.get('MT5_SERVER').strip(),
        'TP_MANAGEMENT': {
            3: [1, 2],
            4: [0, 2, 3],
            10: [8,9]
        },
        'VANTAGE_SYMBOL_MAP':{
            'US30': 'DJ30',
        }
    }
    config['TG'] = {
        'ID': os.environ.get('TELEGRAM_API_ID'),
        'HASH': os.environ.get('TELEGRAM_API_HASH'),
        'PHONE': os.environ.get('TELEGRAM_PHONE')
    }

    return config

def initialize_logger():
    # Create a logger object
    logger = logging.getLogger('telegramMetatrader5')
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)


def parse_message(message):
    data = {}
    # Extract symbol, direction, and entry price
    match = re.search(r'([\w+]+)\s+(BUY|SELL)\s+@\s+(\d+)', message)
    if match:
        data['symbol'] = match.group(1)
        data['direction'] = match.group(2)
        data['entry_price'] = match.group(3)

    # Extract SL
    match = re.search(r'SL-\s*(\d+)', message)
    if match:
        data['SL'] = match.group(1)

    # Extract TPs
    tps = re.findall(r'TP\d+-\s*(\d+)', message)
    if tps:
        data['TPs'] = {f"TP{i}": int(tps[i]) for i in range(0, len(tps), 1)}

    be = re.findall(r'\b(?:BE|be|Break Even|break even)\b', message)
    if be:
        data['BE'] = True

    if data == {}:
        logger.error(f"Could not parse message: {message}")
        return None

    return data


def find_modified_properties(dict1, dict2):
    modified = {}
    all_keys = set(dict1.keys()).union(set(dict2.keys()))

    for key in all_keys:
        if key not in dict1:
            modified[key] = dict2[key]
        elif key not in dict2:
            modified[key] = dict1[key]
        elif dict1[key] != dict2[key]:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                nested_modified = find_modified_properties(dict1[key], dict2[key])
                if nested_modified:
                    modified[key] = nested_modified
            else:
                modified[key] = (dict1[key], dict2[key])

    return modified


def create_trade_dicts(trade_dict, tp_config, symbol_config):
    tps = trade_dict.get('TPs', {})
    if not isinstance(tps, dict) or not tps:
        tps = {'TP0': None}

    tp_keys = list(tps.keys())
    tp_length = len(tp_keys)
    trade_dicts = []

    if tp_length == 1 and tps.get('TP0') is None:
        new_trade_dict = {
            'symbol': symbol_config.get(trade_dict['symbol'], trade_dict['symbol']),
            'direction': trade_dict['direction'],
            'entry_price': trade_dict['entry_price'],
            'SL': trade_dict['SL'],
            'TP': '0'
        }
        trade_dicts.append(new_trade_dict)
    else:
        selected_tps = tp_config[tp_length]

        for tp_index in selected_tps:
            new_trade_dict = {
                'symbol': symbol_config.get(trade_dict['symbol'], trade_dict['symbol']),
                'direction': trade_dict['direction'],
                'entry_price': trade_dict['entry_price'],
                'SL': trade_dict['SL'],
                'TP': tps[tp_keys[tp_index]] if tps[tp_keys[tp_index]] is not None else None
            }
            trade_dicts.append(new_trade_dict)

    return trade_dicts
