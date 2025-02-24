import asyncio
import logging
from utility import read_env_vars
from metatraderHandler import MetatraderHandler
from telegramHandler import TelegramHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

async def main():
    """Main function to run the application."""
    config = read_env_vars()
    metatraderHandler = MetatraderHandler(
        config['MT5']['ACCOUNT'],
        config['MT5']['PASSWORD'],
        config['MT5']['SERVER']
    )

    telegram_handler = TelegramHandler(config, metatraderHandler)

    while True:
        try:
            await telegram_handler.start()
        except (ConnectionError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Connection error: {e}, restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())