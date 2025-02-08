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

    def open_multiple_trades(self, trades):
        results = []
        trades_len = len(trades) if len(trades) > 1 else 2
        for i in range(trades_len):
            element = trades[i] if len(trades) > 1 else trades[0]
            results.append(self.open_trade(element, 0.1))

        return results


    def open_trade(self, trade_details, volume):
        tick = mt5.symbol_info_tick(trade_details['symbol']) 
        if tick is None:
            self.logger.error(f"Symbol {trade_details['symbol']} not found or not available")
            return

        symbol_info = mt5.symbol_info(trade_details['symbol'])
        if symbol_info is None:
            self.logger.error(f"Symbol {trade_details['symbol']} not found")
            return

        if not symbol_info.visible:
            self.logger.info(f"Symbol {trade_details['symbol']} is not visible, trying to add it")
            if not mt5.symbol_select(trade_details['symbol'], True):
                self.logger.error(f"Failed to add symbol {trade_details['symbol']}")
                return

        if trade_details['direction'].lower() == 'buy':
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif trade_details['direction'].lower() == 'sell':
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            self.logger.error("Invalid action")
            return

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": trade_details['symbol'],
            "volume": float(volume),
            "type": order_type,
            "price": float(price),
            "sl": float(trade_details['SL']),
            "tp": float(trade_details['TP']),
            "deviation": 20,
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

    def update_stoploss(self, trade_ids):
        if not isinstance(trade_ids, list):
            trade_ids = [trade_ids]

        for trade_id in trade_ids:
            position = mt5.positions_get(ticket=trade_id)
            if not position:
                self.logger.error(f"Position with trade ID {trade_id} not found")
                continue

            position = position[0]
            entry_price = position.price_open

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "sl": entry_price,
                "tp": position.tp,
                "position": trade_id,
            }

            try:
                result = mt5.order_send(request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    self.logger.error(f"Failed to update stoploss for trade ID {trade_id}, retcode = {result.retcode if result else 'None'}")
                else:
                    self.logger.info(f"Stoploss updated to BE for trade ID {trade_id}")
            except Exception as e:
                self.logger.error(f"Exception occurred while updating stoploss for trade ID {trade_id}: {e}")

    def update_trade(self):
        pass