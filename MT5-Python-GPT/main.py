import logging
from business.metatraderHandler import MetatraderHandler
from data.dbHandler import dbHandler
import asyncio
from business.tradesAnalyzerHandler import tradesAnalyzer
from business.telegramAnalyzer import TelegramAnalyzer
from utility.utility import compare_trades_still_open, read_env_vars

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
    mt5_env = "MT5_DEV" if config['ENV'] == 'DEV' else "MT5"
    db = dbHandler(config=config)
    metatrader = MetatraderHandler(
        account=config[mt5_env]['ACCOUNT'],
        password=config[mt5_env]['PASSWORD'],
        server=config[mt5_env]['SERVER']
    )
    analyzer = TelegramAnalyzer(config=config, dbHandler=db, metatraderHandler=metatrader)

    async def run_analyzer():
        while True:
            try:
                await analyzer.start()
            except (ConnectionError, asyncio.TimeoutError, OSError) as e:
                logger.warning(f"❌ Connection error: {e}, restarting in 5 seconds...")
                await asyncio.sleep(5)

    async def check_metatrader():
        while True:
            compare_trades_still_open(db,metatrader)
            # Add your logic to check metatrader here
            await asyncio.sleep(10)  # Example sleep, replace with actual logic

    await asyncio.gather(run_analyzer(), check_metatrader())

if __name__ == "__main__":
    asyncio.run(main())