import logging
from business.metatraderHandler import MetatraderHandler
from data.dbHandler import dbHandler
import asyncio
from business.tradesAnalyzerHandler import tradesAnalyzer
from business.telegramAnalyzer import TelegramAnalyzer
from utility.utility import compare_trades_still_open, read_env_vars, update_config_with_accounts

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

async def main():
    config = read_env_vars()
    db = dbHandler(config=config)
    accounts = db.get_software_accounts_based_on_env(config['ENV'].lower())
    metatrader_handles = []
    for account in accounts:
        config.update(update_config_with_accounts(account,config))
        metatrader = MetatraderHandler(
            account=config["MT5"]['ACCOUNT'],
            password=config["MT5"]['PASSWORD'],
            server=config["MT5"]['SERVER']
        )
        metatrader_handles.append(metatrader)
    analyzer = TelegramAnalyzer(config=config, dbHandler=db, metatraderHandlers=metatrader_handles)

    async def run_analyzer():
        while True:
            try:
                await analyzer.start()
            except (ConnectionError, asyncio.TimeoutError, OSError) as e:
                logger.warning(f"❌ Connection error: {e}, restarting in 5 seconds...")
                await asyncio.sleep(5)

    async def check_metatrader():
        while True:
            for mt in metatrader_handles:
                compare_trades_still_open(db,mt)
            # Add your logic to check metatrader here
            await asyncio.sleep(10)  # Example sleep, replace with actual logic

    await asyncio.gather(run_analyzer(), check_metatrader())

if __name__ == "__main__":
    asyncio.run(main())