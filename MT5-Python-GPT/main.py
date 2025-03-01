from data.dbHandler import dbHandler
import asyncio
from business.tradesAnalyzerHandler import tradesAnalyzer
from business.telegramAnalyzer import TelegramAnalyzer
from utility.utility import read_file, initialize_logger, read_env_vars

logger = initialize_logger()

async def main():
    config = read_env_vars()
    db = dbHandler(config=config)
    analyzer = TelegramAnalyzer(config=config, dbHandler=db)

    while True:
        try:
            await analyzer.start()
        except (ConnectionError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"❌ Connection error: {e}, restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())