import logging
import os

logger = logging.getLogger("telegramListener")

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

def initialize_logger():
    # Create a logger object
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

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