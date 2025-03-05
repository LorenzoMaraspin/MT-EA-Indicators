import logging
from business.metatraderHandler import MetatraderHandler
from data.dbHandler import dbHandler
import asyncio
from business.tradesAnalyzerHandler import tradesAnalyzer
from business.telegramAnalyzer import TelegramAnalyzer
from utility.utility import read_file, read_env_vars

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
    metatrader = MetatraderHandler(
        account=config['MT5']['ACCOUNT'],
        password=config['MT5']['PASSWORD'],
        server=config['MT5']['SERVER']
    )
    analyzer = TelegramAnalyzer(config=config, dbHandler=db, metatraderHandler=metatrader)

    while True:
        try:
            await analyzer.start()
        except (ConnectionError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"❌ Connection error: {e}, restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())