import logging
import MetaTrader5 as mt5
from data.trade import Trade
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
        self.initialized = False

    def initialize_mt5(self) -> bool:
        """
        Initialize and log in to the MetaTrader 5 terminal.

        Returns:
            bool: True if initialization and login are successful, False otherwise.
        """
        if not self.initialized:
            if not mt5.initialize():
                logger.error("initialize() failed, error code = %s", mt5.last_error())
                return False

            if not mt5.login(login=self.account, password=self.password, server=self.server):
                logger.error("login() failed, error code = %s", mt5.last_error())
                mt5.shutdown()
                return False

            logger.info("MetaTrader 5 initialized and logged in successfully.")
            self.initialized = True
        return True

    def shutdown_mt5(self) -> None:
        """Shutdown the MetaTrader 5 terminal."""
        if self.initialized:
            mt5.shutdown()
            logger.info("MetaTrader 5 shutdown successfully.")
            self.initialized = False

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
            "volume": float(trade_details['lot_size']),
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
            logger.info(f"Order placed successfully. {result.order}")
            return result.order
        except Exception as e:
            logger.error("Exception occurred: %s", e)
            return None
    """
    def update_trade_break_even(self, order_id, new_sl: Optional[float] = None):

        position = mt5.positions_get(ticket=int(order_id))
        if not position:
            logger.error(f"Position with trade ID {order_id} not found.")
            return None

        position = position[0]
        symbol_info = mt5.symbol_info(position.symbol)

        if not symbol_info:
            logger.error(f"Symbol info not found for {position.symbol}")
            return None

        price_open = position.price_open
        sl_target = new_sl if new_sl is not None else price_open
        point = symbol_info.point
        digits = symbol_info.digits
        stop_level = symbol_info.trade_stops_level * point

        # Tentativi di mettere a BE
        for attempt in range(3):
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "sl": float(sl_target),
                "tp": float(position.tp),
                "position": int(order_id),
            }

            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"[Attempt {attempt + 1}/3] SL set to BE for trade ID {order_id}")
                return sl_target
            else:
                logger.warning(
                    f"[Attempt {attempt + 1}/3] Failed to set SL to BE. Retcode: {result.retcode if result else 'None'}")

        # Fallback: SL valido più vicino possibile all'entry price
        logger.info(f"All 3 attempts to set SL to BE failed. Trying fallback...")

        if position.type == mt5.ORDER_TYPE_BUY:
            min_sl = position.price_current - stop_level
            fallback_sl = max(min_sl, price_open - 2 * stop_level)
        elif position.type == mt5.ORDER_TYPE_SELL:
            min_sl = position.price_current + stop_level
            fallback_sl = min(min_sl, price_open + 2 * stop_level)
        else:
            logger.error("Unknown position type.")
            return None

        request["sl"] = round(fallback_sl, digits)
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"SL fallback set near entry price for trade ID {order_id}")
            return fallback_sl
        else:
            logger.error(
                f"Fallback SL update failed for trade ID {order_id}, retcode: {result.retcode if result else 'None'}")
            return None

    """
    def update_trade_break_even(self, order_id, new_sl: Optional[float] = None):
        """
        Update the stop loss to break even for a given trade.

        Args:
            order_id (int): The ID of the trade to update.
            new_sl (Optional[float]): New stop loss value, defaults to the entry price if not provided.

        Returns:
            Optional[float]: The new stop loss value if successful, None otherwise.
        """

        position = mt5.positions_get(ticket=int(order_id))
        if not position:
            logger.error(f"Position with trade ID {order_id} not found.")
            return None

        position = position[0]
        stoploss = new_sl if new_sl is not None else position.price_open

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "sl": float(stoploss),
            "tp": float(position.tp),
            "position": int(order_id),
        }

        try:
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Failed to update stoploss/takeprofit for trade ID {order_id}, retcode = {result.retcode if result else 'None'}")
                if result.retcode == 10016:  # Invalid stop loss
                    logger.error(f"Invalid stop loss value for trade ID {order_id}.")
                    self.close_trade(order_id)
                return None
            else:
                logger.info(f"Stoploss/Takeprofit updated for trade ID {order_id}")
                return float(stoploss)
        except Exception as e:
            logger.error(f"Exception occurred while updating stoploss/takeprofit for trade ID {order_id}: {e}")
            return None

    def update_trade(self, order_id, new_sl: Optional[float] = None, new_tps: Optional[float] = None) -> None:
        """
        Update stop loss and take profit for a trade.

        Args:
            order_id (int): The ID of the trade to update.
            new_sl (Optional[float]): New stop loss value.
            new_tps (Optional[float]): New take profit value.
        """


        position = mt5.positions_get(ticket=int(order_id))
        if not position:
            logger.error(f"Position with trade ID {order_id} not found.")
            return None

        position = position[0]
        stoploss = new_sl if new_sl is not None else position.sl
        takeprofits = new_tps if new_tps is not None else position.tp

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "sl": float(stoploss),
            "tp": float(takeprofits),
            "position": int(order_id),
        }

        try:
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Failed to update stoploss/takeprofit for trade ID {order_id}, retcode = {result.retcode if result else 'None'}")
            else:
                logger.info(f"Stoploss/Takeprofit updated for trade ID {order_id}")
        except Exception as e:
            logger.error(f"Exception occurred while updating stoploss/takeprofit for trade ID {order_id}: {e}")

    def close_trade(self, order_id: int) -> Optional[int]:
        """
        Close a trade based on the provided order ID.

        Args:
            order_id (int): The ID of the trade to close.

        Returns:
            Optional[int]: The result code of the close operation if successful, None otherwise.
        """


        position = mt5.positions_get(ticket=int(order_id))
        if not position:
            logger.error(f"Position with trade ID {order_id} not found.")
            return None

        position = position[0]
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "position": int(order_id),
            "price": mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask,
            "magic": 0,
            "comment": "Close trade",
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        try:
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Failed to close trade ID {order_id}, retcode = {result.retcode if result else 'None'}")
                return None
            logger.info(f"Trade ID {order_id} closed successfully.")
            return result.retcode
        except Exception as e:
            logger.error(f"Exception occurred while closing trade ID {order_id}: {e}")
            return None

    def get_all_position(self) -> List[int]:
        """
        Get all open positions.

        Returns:
            List[int]: List of open position tickets.
        """
        logger.setLevel(logging.CRITICAL)

        try:
            positions = mt5.positions_get()
            if positions is None:
                logger.error("No positions found, error code = %s", mt5.last_error())
                return []

            open_positions = [position.ticket for position in positions]
            logger.setLevel(logging.INFO)
            return open_positions
        except Exception as e:
            logger.error("Exception occurred while getting all positions: %s", e)
            return []

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