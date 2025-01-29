import os
import logging
import re


def read_env_vars():
    config = {}
    config['MT5'] = {
        'ACCOUNT': int(os.environ.get('MT5_ACCOUNT')),
        'PASSWORD': os.environ.get('MT5_PASSWORD').strip(),
        'SERVER': os.environ.get('MT5_SERVER').strip(),
        'TP_MANAGEMENT': {
            3: [1, 2],
            4: [0, 2, 3],
            10: [0, 2, 4, 6, 8]
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

def search_for_trading_signal(message: str):
    keywords = ['TP', 'takeprofit', 'SL', 'stoploss', 'entry', 'buy', 'sell', 'long', 'short', 'entryprice', 'symbol', 'pair', 'stop loss', 'take profit']
    results = {}

    for keyword in keywords:
        pattern = re.compile(rf'\b{re.escape(keyword)}\b', re.IGNORECASE)
        match = pattern.search(message)
        if match:
            results[keyword] = match.group(0)

    return results

def parse_message(message):
    data = {}
    # Extract symbol, direction, and entry price
    match = re.search(r'([\w+]+)\s+(BUY|SELL)\s+@\s+(\d+)', message)
    if match:
        data['symbol'] = match.group(1)
        data['direction'] = match.group(2)
        data['entry_price'] = int(match.group(3))

    # Extract SL
    match = re.search(r'SL-\s*(\d+)', message)
    if match:
        data['SL'] = int(match.group(1))

    # Extract TPs
    tps = re.findall(r'TP\d+-\s*(\d+)', message)
    data['TPs'] = {f"TP{i}": int(tps[i]) for i in range(0, len(tps), 1)}

    return data

def find_modified_properties(dict1, dict2):
    modified = {}
    for key in dict1:
        if key in dict2:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                nested_modified = find_modified_properties(dict1[key], dict2[key])
                if nested_modified:
                    modified[key] = nested_modified
            elif dict1[key] != dict2[key]:
                modified[key] = (dict1[key], dict2[key])
    return modified


def create_trade_dicts(message_text, tp_config, symbol_config):
    trade_dict = parse_message(message_text)

    tps = trade_dict['TPs']
    tp_keys = list(tps.keys())
    tp_length = len(tp_keys)

    if tp_length not in tp_config:
        raise ValueError(f"No configuration found for TP length: {tp_length}")

    selected_tps = tp_config[tp_length]
    trade_dicts = []

    for tp_index in selected_tps:
        tp_key = tp_keys[tp_index]  # Convert 1-based index to 0-based
        new_trade_dict = {
            'symbol':symbol_config[trade_dict['symbol']] if trade_dict['symbol'] in symbol_config else trade_dict['symbol'],
            'direction': trade_dict['direction'],
            'entry_price': trade_dict['entry_price'],
            'SL': trade_dict['SL'],
            'TP': tps[tp_key]
        }
        trade_dicts.append(new_trade_dict)

    return trade_dicts