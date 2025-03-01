import logging
import MetaTrader5 as mt5
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class MetatraderHandler:
    def __init__(self, account: int, password: str, server: str):
        """
        Initialize the MetaTrader handler.

        Args:
            account (int): MetaTrader account number.
            password (str): MetaTrader account password.
            server (str): MetaTrader server name.
        """
        self.account = account
        self.password = password
        self.server = server
        self.initialize_mt5()

    def initialize_mt5(self) -> bool:
        """
        Initialize and log in to the MetaTrader 5 terminal.

        Returns:
            bool: True if initialization and login are successful, False otherwise.
        """
        if not mt5.initialize():
            logger.error("initialize() failed, error code = %s", mt5.last_error())
            return False

        if not mt5.login(login=self.account, password=self.password, server=self.server):
            logger.error("login() failed, error code = %s", mt5.last_error())
            mt5.shutdown()
            return False

        logger.info("MetaTrader 5 initialized and logged in successfully.")
        return True

    def shutdown_mt5(self) -> None:
        """Shutdown the MetaTrader 5 terminal."""
        mt5.shutdown()
        logger.info("MetaTrader 5 shutdown successfully.")

    def open_multiple_trades(self, trades: List[Dict[str, Union[str, float]]], minimum_trade_count: int) -> List[int]:
        """
        Open multiple trades based on the provided trade details.

        Args:
            trades (List[Dict[str, Union[str, float]]]): List of trade details.
            minimum_trade_count (int): Minimum number of trades to open.

        Returns:
            List[int]: List of trade IDs for successfully opened trades.
        """
        results = []
        trades_len = max(len(trades), minimum_trade_count)

        for i in range(trades_len):
            trade_details = trades[i] if len(trades) > 1 else trades[0]
            trade_id = self.open_trade(trade_details)
            if trade_id:
                results.append(trade_id)

        return results

    def preparation_trade(self, symbol: str, direction: str) -> Optional[Tuple[int, float]]:
        """
        Prepare trade details for execution.

        Args:
            symbol (str): Trading symbol.
            direction (str): Trade direction (e.g., 'buy', 'sell').

        Returns:
            Optional[Tuple[int, float]]: Tuple containing order type and price, or None if preparation fails.
        """
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"Symbol {symbol} not found or not available.")
            return None

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Symbol {symbol} not found.")
            return None

        if not symbol_info.visible:
            logger.info(f"Symbol {symbol} is not visible, trying to add it.")
            if not mt5.symbol_select(symbol, True):
                logger.error(f"Failed to add symbol {symbol}.")
                return None

        direction = direction.lower()
        order_types = {
            'buy': mt5.ORDER_TYPE_BUY,
            'sell': mt5.ORDER_TYPE_SELL,
            'buy stop': mt5.ORDER_TYPE_BUY_STOP,
            'sell stop': mt5.ORDER_TYPE_SELL_STOP,
            'buy limit': mt5.ORDER_TYPE_BUY_LIMIT,
            'sell limit': mt5.ORDER_TYPE_SELL_LIMIT,
        }

        if direction not in order_types:
            logger.error(f"Invalid action: {direction}.")
            return None

        order_type = order_types[direction]
        price = tick.ask if 'buy' in direction else tick.bid
        return order_type, price

    def open_trade(self, trade_details: Dict[str, Union[str, float]]) -> Optional[int]:
        """
        Open a single trade based on the provided trade details.

        Args:
            trade_details (Dict[str, Union[str, float]]): Trade details including symbol, direction, volume, SL, and TP.

        Returns:
            Optional[int]: Trade ID if successful, None otherwise.
        """
        preparation_result = self.preparation_trade(trade_details['symbol'], trade_details['direction'])
        if preparation_result is None:
            return None

        order_type, price = preparation_result
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
                logger.error("Failed to send order.")
                return None
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error("Order failed, retcode = %s", result.retcode)
                return None
            logger.info("Order placed successfully.")
            return result.order
        except Exception as e:
            logger.error("Exception occurred: %s", e)
            return None

    def update_trade(self, trade_ids: Union[int, List[int]], new_sl: Optional[float] = None, new_tps: Optional[float] = None) -> None:
        """
        Update stop loss and take profit for one or more trades.

        Args:
            trade_ids (Union[int, List[int]]): Trade ID or list of trade IDs.
            new_sl (Optional[float]): New stop loss value.
            new_tps (Optional[float]): New take profit value.
        """
        if not isinstance(trade_ids, list):
            trade_ids = [trade_ids]

        for i in range (0,len(trade_ids),1):
            trade_id = trade_ids[i]
            position = mt5.positions_get(ticket=trade_id)
            if not position:
                logger.error(f"Position with trade ID {trade_id} not found.")
                continue

            position = position[0]
            stoploss = new_sl if new_sl is not None else position.sl
            takeprofits = new_tps[len(new_tps) - 1 - i] if new_tps is not None else position.tp

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
                    logger.error(f"Failed to update stoploss/takeprofit for trade ID {trade_id}, retcode = {result.retcode if result else 'None'}")
                else:
                    logger.info(f"Stoploss/Takeprofit updated for trade ID {trade_id}")
            except Exception as e:
                logger.error(f"Exception occurred while updating stoploss/takeprofit for trade ID {trade_id}: {e}")

    def get_account_balance(self) -> Optional[float]:
        """
        Get the current account balance.

        Returns:
            Optional[float]: Account balance if successful, None otherwise.
        """
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Failed to get account info, error code = %s", mt5.last_error())
            return None
        return account_info.balance