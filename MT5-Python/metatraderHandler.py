import json
import time

import MetaTrader5 as mt5
import logging

logger = logging.getLogger(__name__)
class MetatraderHandler:
    def __init__(self, account, password, server):
        self.logger = logging.getLogger(__name__)
        self.account = account
        self.password = password
        self.server = server
        self.initialize_mt5()

    def initialize_mt5(self):
        if not mt5.initialize():
            self.logger.error("initialize() failed, error code = %s", mt5.last_error())
            return False
        if not mt5.login(login=self.account, password=self.password, server=self.server):
            self.logger.error("login() failed, error code = %s", mt5.last_error())
            mt5.shutdown()
            return False
        return True

    def shutdown_mt5(self):
        mt5.shutdown()

    def open_multiple_trades(self, trades, minimu_trade_count):
        results = []

        trades_len = len(trades) if len(trades) > 1 else minimu_trade_count
        for i in range(trades_len):
            element = trades[i] if len(trades) > 1 else trades[0]
            results.append(self.open_trade(element))

        return results

    def preparation_trade(self, symbol, direction):
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            self.logger.error(f"Symbol {symbol} not found or not available")
            return

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            self.logger.error(f"Symbol {symbol} not found")
            return

        if not symbol_info.visible:
            self.logger.info(f"Symbol {symbol} is not visible, trying to add it")
            if not mt5.symbol_select(symbol, True):
                self.logger.error(f"Failed to add symbol {symbol}")
                return

        if direction.lower() == 'buy':
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif direction.lower() == 'sell':
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        elif direction.lower() == 'buy stop':
            order_type = mt5.ORDER_TYPE_BUY_STOP
            price = tick.ask
        elif direction.lower() == 'sell stop':
            order_type = mt5.ORDER_TYPE_SELL_STOP
            price = tick.bid
        elif direction.lower() == 'buy limit':
            order_type = mt5.ORDER_TYPE_BUY_LIMIT
            price = tick.ask
        elif direction.lower() == 'sell limit':
            order_type = mt5.ORDER_TYPE_SELL_LIMIT
            price = tick.bid
        else:
            self.logger.error("Invalid action")
            return
        return order_type, price

    def open_trade(self, trade_details):
        order_type, price = self.preparation_trade(trade_details['symbol'], trade_details['direction'])
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": trade_details['symbol'],
            "volume": float(trade_details['volume']),
            "type": order_type,
            "price": float(price),
            "sl": float(trade_details['SL']),
            "tp": float(trade_details['TP']),
            "comment": "Trade from Telegram",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        try:
            result = mt5.order_send(request)
            if result is None:
                self.logger.error("Failed to send order")
                return
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error("Order failed, retcode = %s", result.retcode)
            else:
                self.logger.info("Order placed successfully")
                return result.order
        except Exception as e:
            self.logger.error("Exception occurred: %s", e)

    def update_trade (self, trade_ids, new_sl=None, new_tps=None):
        if not isinstance(trade_ids, list):
            trade_ids = [trade_ids]

        for trade_id in trade_ids:
            position = mt5.positions_get(ticket=trade_id)
            if not position:
                self.logger.error(f"Position with trade ID {trade_id} not found")
                continue

            position = position[0]
            entry_price = position.price_open

            # Determine the new stoploss value
            if new_sl is not None:
                stoploss = new_sl
            else:
                stoploss = entry_price

            # Determine the new takeprofit values
            takeprofits = new_tps if new_tps is not None else position.tp

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "sl": float(stoploss),
                "tp": float(takeprofits),
                "position": trade_id,
            }

            try:
                result = mt5.order_send(request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    self.logger.error(f"Failed to update stoploss/takeprofit for trade ID {trade_id}, retcode = {result.retcode if result else 'None'}")
                else:
                    self.logger.info(f"Stoploss/Takeprofit updated for trade ID {trade_id}")
            except Exception as e:
                self.logger.error(f"Exception occurred while updating stoploss/takeprofit for trade ID {trade_id}: {e}")

    def get_account_balance(self):
        account_info = mt5.account_info()
        if account_info is None:
            self.logger.error("Failed to get account info, error code = %s", mt5.last_error())
            return None
        return account_info.balance
