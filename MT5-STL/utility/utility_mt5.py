from business.mt5Handler import MetatraderHandler  # Importa la tua classe
import time

from data.trade import Trade
from data.tradeUpdate import TradeUpdate
from utility.utility_tg import create_trade_entries
import logging
logger = logging.getLogger(__name__)

def open_trades_multi_account(parsed_text, config, db_message_id):
    trade_results = []
    for mt5 in config["MT5"]:
        mt_handler= MetatraderHandler(account=mt5["ACCOUNT"], password=mt5["PASSWORD"], server=mt5["SERVER"])
        mt_handler.initialize_mt5()
        trades = create_trade_entries(parsed_text, db_message_id, mt5)
        n_trades_to_open = len(trades) if len(trades) > 1 else trades[0]["n_trades"]
        for i in range(0, n_trades_to_open, 1):
            trade = trades[i] if len(trades) > 1 else trades[0]
            trade_id = mt_handler.open_trade(trade)
            if trade_id:
                trade = Trade(
                    msg_id=int(trade['db_message_id']),
                    order_id=int(trade_id),
                    status='open',
                    break_even=0.0,
                    symbol=trade['symbol'],
                    direction=trade['direction'],
                    volume=trade['lot_size'],
                    stop_loss=trade['SL'],
                    take_profit=trade['TP'],
                    entry_price=trade['entry_price'],
                    account_id=int(trade['account_id'])
                )
                trade_results.append(trade)
    return trade_results

def update_trades_multi_account(trades_to_update, config, msg_parsed_text, db_message_id, msg_raw_text):
    trade_updates_result, trades_updated = [], []
    for mt5 in config["MT5"]:
        mt_handler= MetatraderHandler(account=mt5["ACCOUNT"], password=mt5["PASSWORD"], server=mt5["SERVER"])
        mt_handler.initialize_mt5()
        trades = create_trade_entries(msg_parsed_text, db_message_id, mt5)
        subset_trades_to_update = [item for item in trades_to_update if item.account_id == mt5["ACCOUNT"]]
        for i in range(0, len(subset_trades_to_update), 1):
            trade = subset_trades_to_update[i]
            if trade.account_id == mt5["ACCOUNT"] :
                new_sl = trades[i]['SL'] if 'SL' in trades[i] and trades[i]['SL'] != 0 else None
                new_tp = trades[i]['TP'] if 'TP' in trades[i] and trades[i]['TP'] != 0 else None
                mt_handler.update_trade(trade.order_id, new_sl, new_tp)
                trade.stop_loss = new_sl
                trade.take_profit = new_tp
                trade_update = TradeUpdate(
                    trade_id=trade.trade_id,
                    order_id=trade.order_id,
                    account_id=trade.account_id,
                    update_action="UPDATE",
                    update_body=msg_raw_text
                )
                trade_updates_result.append(trade_update)
                trades_updated.append(trade)
            else:
                continue
    return trades_updated, trade_updates_result

def update_trades_be_multi_account(trades_to_update, config, msg_parsed_text, msg_raw_text):
    trade_updates_result = []
    for mt5 in config["MT5"]:
        mt_handler= MetatraderHandler(account=mt5["ACCOUNT"], password=mt5["PASSWORD"], server=mt5["SERVER"])
        mt_handler.initialize_mt5()
        for trade in trades_to_update:
            if trade.account_id == mt5["ACCOUNT"]:
                new_sl = msg_parsed_text['stop_loss'] if msg_parsed_text['stop_loss'] is not None and msg_parsed_text[
                    'stop_loss'] != 0 else None
                updated_sl = mt_handler.update_trade_break_even(trade.order_id, new_sl)
                if updated_sl:
                    trade.stop_loss = updated_sl
                    trade.break_even = updated_sl
                    trade_update = TradeUpdate(
                        trade_id=trade.trade_id,
                        order_id=trade.order_id,
                        account_id=trade.account_id,
                        update_action="BE",
                        update_body=msg_raw_text
                    )
                    trade_updates_result.append(trade_update)
            else:
                continue
    return trades_to_update, trade_updates_result

def close_trades_multi_account(trades_to_close, config, msg_raw_text):
    trade_updates_result = []
    for mt5 in config["MT5"]:
        mt_handler= MetatraderHandler(account=mt5["ACCOUNT"], password=mt5["PASSWORD"], server=mt5["SERVER"])
        mt_handler.initialize_mt5()
        for trade in trades_to_close:
            if trade.account_id == mt5["ACCOUNT"]:
                response_close = mt_handler.close_trade(trade.order_id)
                if response_close:
                    trade.status = 'close'
                    trade_update = TradeUpdate(
                        trade_id=trade.trade_id,
                        order_id=trade.order_id,
                        account_id=trade.account_id,
                        update_action="CLOSE",
                        update_body=msg_raw_text
                    )
                    trade_updates_result.append(trade_update)
            else:
                continue
    return trades_to_close, trade_updates_result

def verify_open_trades_or_be(config, db):
    for mt5 in config["MT5"]:
        mt_handler = MetatraderHandler(account=mt5["ACCOUNT"], password=mt5["PASSWORD"], server=mt5["SERVER"])
        open_trades_db = db.get_all_trades(mt5["ACCOUNT"])
        if open_trades_db:
            mt_handler.initialize_mt5()
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


