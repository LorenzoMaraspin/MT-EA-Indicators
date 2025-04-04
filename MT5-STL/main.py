import logging
from business.mt5Handler import MetatraderHandler
from data.dbHandler import dbHandler
import asyncio
import threading
from business.tgHandler import TelegramAnalyzer
from utility.utillty_config import read_env_file, get_sw_configuration_by_account
from utility.utility_mt5 import verify_open_trades_or_be
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartTradeAnalyzer")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

env_dict = read_env_file('utility/config.env')
db = dbHandler(env_dict)

async def main():
    accounts = db.get_software_accounts_based_on_env(env_dict['ENV'].lower())
    account_config = get_sw_configuration_by_account(accounts)
    account_config.update(env_dict)
    analyzer = TelegramAnalyzer(config=account_config, db_handler=db)

    async def run_analyzer():
        while True:
            try:
                await analyzer.start()
            except (ConnectionError, asyncio.TimeoutError, OSError) as e:
                logger.warning(f"❌ Connection error: {e}, restarting in 5 seconds...")
                await asyncio.sleep(5)

    async def check_metatrader():
        while True:
            verify_open_trades_or_be(account_config,db)
    #await asyncio.gather(run_analyzer(), check_metatrader())
    #await asyncio.gather(run_analyzer())
    def start_run_analyzer():
        asyncio.run(run_analyzer())

    def start_check_metatrader():
        asyncio.run(check_metatrader())

    thread_analyzer = threading.Thread(target=start_run_analyzer)
    thread_metatrader = threading.Thread(target=start_check_metatrader)
    thread_analyzer.start()
    thread_metatrader.start()
    thread_analyzer.join()
    thread_metatrader.join()


if __name__ == "__main__":
    asyncio.run(main())