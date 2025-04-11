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
    customized_dict = {
        "DB": {
            "HOST": env_dict.get("DB_HOST"),
            "DBNAME": env_dict.get("DB_NAME") if env_dict.get("ENVIRONMENT") == "PROD" else env_dict.get("DB_NAME_DEV"),
            "PORT": int(env_dict.get("DB_PORT", 5432)),
            "USER": env_dict.get("DB_USER"),
            "PASSWORD": env_dict.get("DB_PWD")
        },
        "ENV": env_dict.get("ENVIRONMENT", "DEV"),
        "MT5_ACTIVE_ACCOUNT": env_dict.get("MT5_ACTIVE_ACCOUNT"),
    }
    return customized_dict