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
            3: [2,3],
            4: [3, 4],
            5: [3,5],
            6: [4, 5, 6],
            7: [5,6,7],
            8: [6, 7, 8],
            9: [7, 8, 9],
            10: [8,9,10]
        },
        'VANTAGE_SYMBOL_MAP':{
            'US30': 'DJ30',
            'GOLD':'XAUUSD+',
            'XAUUSD':'XAUUSD+'
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
    config['ENV'] = os.environ.get('ENVIRONMENT')

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
    patterns = {
        'symbol': r'(?P<symbol>[\w+]+)\s+(?P<direction>BUY|SELL|BUY LIMIT|BUY STOP|SELL LIMIT|SELL STOP)\s+@\s+(?P<entry_price>\d+)',
        'SL': r'SL-\s*(\d+)',
        'TPs': r'TP\d+-\s*(\d+)',
        'BE': r'\b(?:BE|Break Even)\b'
    }

    # Extract symbol, direction, and entry price
    match = re.search(patterns['symbol'], message, re.IGNORECASE)
    if match:
        data['symbol'] = match.group('symbol')
        data['direction'] = match.group('direction')
        data['entry_price'] = match.group('entry_price')

    # Extract other patterns
    for key, pattern in patterns.items():
        if key == 'symbol':
            continue
        matches = re.findall(pattern, message, re.IGNORECASE)
        if matches:
            if key == 'TPs':
                data[key] = {f"TP{i}": int(matches[i]) for i in range(len(matches))}
            elif key == 'BE':
                data[key] = True
            else:
                data[key] = matches[0]

    if not data:
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
            'SL': trade_dict['SL'] if 'SL' in trade_dict else '0',
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
                'SL': trade_dict['SL'] if 'SL' in trade_dict else '0',
                'TP': tps[tp_keys[tp_index-1]] if tps[tp_keys[tp_index-1]] is not None else None
            }
            trade_dicts.append(new_trade_dict)

    return trade_dicts
