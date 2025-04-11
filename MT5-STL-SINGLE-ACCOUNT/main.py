import logging
from data.dbHandler import dbHandler
import asyncio
import threading
from utility.config import read_env_file
from business.tgHandler import TelegramAnalyzer
from business.mt5Handler import MetatraderHandler

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
    account_config = db.get_software_account_based_on_id(env_dict['MT5_ACTIVE_ACCOUNT'])
    mt_handler = MetatraderHandler(account=account_config.mt5_account_id, password=account_config.mt5_password, server=account_config.mt5_server)
    tg_analyzer = TelegramAnalyzer(config=account_config.to_dict(), db_handler=db, mt5_handler=mt_handler)

    async def run_analyzer():
        while True:
            try:
                await tg_analyzer.start()
            except (ConnectionError, asyncio.TimeoutError, OSError) as e:
                logger.warning(f"❌ Connection error: {e}, restarting in 5 seconds...")
                await asyncio.sleep(5)

    async def check_metatrader():
        while True:
            await asyncio.sleep(2)
            open_trades_db = db.get_all_trades(account_config.to_dict()['mt5_account_id'])
            if open_trades_db:
                open_trades_mt5 = mt_handler.get_all_position()
                for msg_id, trades in open_trades_db.items():
                    order_ids = [trade.order_id for trade in trades]
                    if not all(order_id in open_trades_mt5 for order_id in order_ids):
                        logger.info(f"Not all order_ids for message {msg_id} are in MT5 positions.")
                        for trade in trades:
                            if trade.order_id not in open_trades_mt5:
                                trade.status = 'close'
                            else:
                                new_sl = mt_handler.update_trade_break_even(trade.order_id, None)
                                trade.stop_loss = new_sl
                                trade.break_even = new_sl
                            db.update_trade(trade)

    #await asyncio.gather(run_analyzer(), check_metatrader())


    def start_check_metatrader():
        asyncio.run(check_metatrader())

    def start_run_analyzer():
        asyncio.run(run_analyzer())

    thread_analyzer = threading.Thread(target=start_run_analyzer)
    thread_metatrader = threading.Thread(target=start_check_metatrader)
    thread_analyzer.start()
    thread_metatrader.start()
    thread_analyzer.join()
    thread_metatrader.join()



if __name__ == "__main__":
    asyncio.run(main())