from dotenv import dotenv_values
from data.account import Account

def read_env_file(file_path: str) -> dict:
    """
    Reads a .env file and returns its content as a customized dictionary.

    Args:
        file_path (str): The path to the .env file.

    Returns:
        dict: A customized dictionary containing the .env file content.
    """
    env_dict = dotenv_values(file_path)

    # Customize the dictionary
    customized_dict = {
        "DB": {
            "HOST": env_dict.get("DB_HOST"),
            "DBNAME": env_dict.get("DB_NAME") if env_dict.get("ENVIRONMENT") == "PROD" else env_dict.get("DB_NAME_DEV"),
            "PORT": int(env_dict.get("DB_PORT", 5432)),
            "USER": env_dict.get("DB_USER"),
            "PASSWORD": env_dict.get("DB_PWD")
        },
        "ENV": env_dict.get("ENVIRONMENT", "DEV")
    }

    return customized_dict

def get_sw_configuration_by_account(accounts: list[Account]):
    config, tmp = {},{}
    tmp["MT5_CONF"] = {
        "ftmo": {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "n_trades": 2,
                "lot_size": 0.04
            },
            "US30": {
                "symbol": "US30.cash",
                "n_trades": 3,
                "lot_size": 0.15
            },
            "EURUSD": {
                "symbol": "EURUSD",
                "n_trades": 2,
                "lot_size": 0.06
            }
        },
        "vantage": {
            "XAUUSD": {
                "symbol": "XAUUSD+",
                "n_trades": 2,
                "lot_size": 0.04
            },
            "US30": {
                "symbol": "DJ30",
                "n_trades": 3,
                "lot_size": 0.20
            },
            "EURUSD": {
                "symbol": "EURUSD+",
                "n_trades": 2,
                "lot_size": 0.06
            }
        },
        "fundingpips": {
            "XAUUSD": {
                "symbol": "XAUUSD",
                "n_trades": 2,
                "lot_size": 0.04
            },
            "US30": {
                "symbol": "DJI30",
                "n_trades": 3,
                "lot_size": 0.02
            },
            "EURUSD": {
                "symbol": "EURUSD",
                "n_trades": 2,
                "lot_size": 0.06
            }
        }
    }
    config["TG"] = {
        "ID": accounts[0].tg_id,
        "HASH": accounts[0].tg_hash,
        "PHONE": accounts[0].tg_phone,
        "SESSION": accounts[0].tg_session,
        "CHANNELS": [int(channel) for channel in accounts[0].tg_channels.split(",")],
        "DST_CHANNEL_GOLD": -1002404066652,
        "DST_CHANNEL_INDEX": -1002535578509
    }
    element = []
    for account in accounts:
        element.append({
            "ACCOUNT": int(account.mt5_account_id),
            "PASSWORD": account.mt5_password,
            "SERVER": account.mt5_server,
            "BROKER": account.mt5_broker,
            "TRADE_MNG": tmp["MT5_CONF"][account.mt5_broker.lower()]
        })

    config["MT5"] = element

    return config


