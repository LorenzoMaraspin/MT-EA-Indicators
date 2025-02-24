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
            2: [1, 2],
            3: [2, 3],
            4: [3, 4],
            5: [3,5],
            6: [4, 5, 6],
            7: [5, 6, 7],
            8: [6, 7, 8],
            9: [7, 8, 9],
            10: [8, 9, 10]
        },
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
    config['ENV'] = os.environ.get('ENVIRONMENT')

    return config

def initialize_logger():
    # Create a logger object
    logger = logging.getLogger('telegramMetatrader5')
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)


def parse_trade_signal(text):
    patterns = {
        'symbol': r'(?P<symbol>[A-Za-z0-9]+)\s+(?P<direction>BUY|SELL|BUY LIMIT|BUY STOP|SELL LIMIT|SELL STOP)\s*@?\s*(?P<entry_price>\d+\.?\d*)',
        'stop_loss': r'(?:SL|stoploss|sl)\s*-?\s*(\d+\.?\d*)',
        'take_profits': r'TP\d+\s*[-:]\s*(\d+\.?\d*)',
        'break_even': r'\b(?:BE|Break Even|Risk Free|Stoploss a prezzo d\'entrata|mettere a BE|mettere a break even|Move SL at BE|Move stop loss at BE|Move stop loss at break even)\b'
    }

    # Verifica se il messaggio è un'istruzione di break even
    if re.search(patterns['break_even'], text, re.IGNORECASE):
        return {'break_even': True}

    trade_info = {
        'symbol': None,
        'direction': None,
        'entry_price': None,
        'stop_loss': None,
        'take_profits': []
    }

    # Estrarre i dati principali (simbolo, direzione, prezzo d'ingresso)
    main_match = re.search(patterns['symbol'], text, re.IGNORECASE)
    if main_match:
        trade_info['symbol'] = main_match.group('symbol').upper()
        trade_info['direction'] = main_match.group('direction').upper()
        trade_info['entry_price'] = float(main_match.group('entry_price'))

    # Estrarre lo stop loss
    sl_match = re.search(patterns['stop_loss'], text, re.IGNORECASE)
    if sl_match:
        trade_info['stop_loss'] = float(sl_match.group(1))

    # Estrarre i take profit
    tp_matches = re.findall(patterns['take_profits'], text, re.IGNORECASE)
    if tp_matches:
        trade_info['take_profits'] = [float(tp) for tp in tp_matches]

    return trade_info


def find_modified_properties(dict1, dict2):
    modified = {}
    all_keys = set(dict1.keys()).union(set(dict2.keys()))

    for key in all_keys:
        if key not in dict2:
            modified[key] = (dict1[key], 0)
        elif dict1[key] != dict2[key]:
            if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                nested_modified = find_modified_properties(dict1[key], dict2[key])
                if nested_modified:
                    modified[key] = nested_modified
            else:
                modified[key] = (dict1[key], dict2[key])

    return modified


def create_trade_dicts(trade_dict, config):
    tps = trade_dict.get('take_profits', {})
    tp_config = config['MT5']['TP_MANAGEMENT']
    symbol_config = config['MT5']['TRADE_MANAGEMENT'][trade_dict['symbol'].upper()]
    if not isinstance(tps, list) or not tps:
        tps = {'TP0': None}

    tp_length = len(tps)
    trade_dicts = []

    if tp_length == 1 and tps.get('TP0') is None:
        new_trade_dict = {
            'symbol': symbol_config['symbol'],
            'direction': trade_dict['direction'],
            'entry_price': trade_dict['entry_price'],
            'volume': symbol_config['default_lot_size'],
            'SL': trade_dict['stop_loss'] if 'stop_loss' in trade_dict and trade_dict['stop_loss'] is not None else '0',
            'TP': '0'
        }
        trade_dicts.append(new_trade_dict)
    else:
        selected_tps = tp_config[tp_length]

        for tp_index in selected_tps:
            new_trade_dict = {
                'symbol': symbol_config['symbol'],
                'direction': trade_dict['direction'],
                'entry_price': trade_dict['entry_price'],
                'volume': symbol_config['default_lot_size'],
                'SL': trade_dict['stop_loss'] if 'stop_loss' in trade_dict and trade_dict['stop_loss'] is not None else '0',
                'TP': tps[tp_index-1] if tps[tp_index-1] is not None else '0'
            }
            trade_dicts.append(new_trade_dict)

    return trade_dicts
