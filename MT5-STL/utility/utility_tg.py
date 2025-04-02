import logging
import re
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def prefilter_message(message: str) -> bool:
    """Prefilter the message to remove unwanted characters."""
    try:
        # Regex patterns to match valid messages
        trade_pattern = re.compile(r'\b[A-Z0-9]+\s+(BUY|SELL|BUY LIMIT|BUY STOP|SELL LIMIT|SELL STOP)\s*@?\s*[0-9\.]+', re.IGNORECASE)
        sl_tp_pattern = re.compile(r'\bSL[-:]\s*[0-9\.]+|TP[0-9]+[-:]\s*[0-9\.]+', re.IGNORECASE)
        update_keywords = ["Move SL at BE","Move SL to BE", "Move SL","Updated", "Update full position", "Close early", "reduce risk", "Close", "Close all", "Close trade"]
        update_keywords_sl = r'\b(?:SL\s*[0-9]+\s*reduce risk|All SL \d+|[A-Za-z]{3,6}\s*SL\s*@\s*\d+|SL\s*[0-9]+\s*both|SL\s*[0-9]+\s*)\b'

        # Check if the message is a trade signal
        if trade_pattern.search(message) or any(keyword.lower() in message.lower() for keyword in update_keywords) or re.search(update_keywords_sl, message, re.IGNORECASE):
            logger.info(f"📨 Valid message received!: {message}")
            return True
        # Check if the message is a SL/TP pattern
        elif sl_tp_pattern.search(message):
            logger.info(f"📨 Valid message received!: {message}")
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"❌ Error in prefiltering message: {e}")
        return False


def extract_trade_data(message: str) -> Optional[Dict[str, Any]]:
    """Extract trade data from a message."""
    patterns = {
        'symbol': r'(?P<symbol>[A-Za-z0-9]+)\s+(?P<direction>BUY|SELL|BUY LIMIT|BUY STOP|SELL LIMIT|SELL STOP)\s*@?\s*(?P<entry_price>\d+\.?\d*)',
        'stop_loss': r'(?:SL|stoploss|sl)\s*-?\s*(\d+\.?\d*)',
        'take_profits': r'TP\d+\s*[-:]\s*(\d+\.?\d*)',
        'break_even': r'\b(?:BE|Break Even|Risk Free|Move SL at BE|Move stop loss at BE|Updated|SL\s*[0-9]+\s*reduce risk|All SL \d+|[A-Za-z]{3,6}\s*SL\s*@\s*\d+|SL\s*[0-9]+\s*both|SL\s*[0-9]+\s*)\b',
        'close_before': r'\b(?:Close early|Close all|Close trade)\b'
    }

    try:
        break_even_match = re.search(patterns['break_even'], message, re.IGNORECASE)
        close_before_match = re.search(patterns['close_before'], message, re.IGNORECASE)
        trade_info = {}
        if break_even_match:
            trade_info['break_even'] = True
            trade_info['message_type'] = 'update'
            # Capture the stop loss value from the matched group
            parts = break_even_match.group(0).split()
            if parts:
                trade_info['symbol'] = str(parts[0]).upper() if re.match(r'^[A-Z]{3,6}$', parts[0]) else None
                number_index = next((i for i, item in enumerate(parts) if any(char.isdigit() for char in item)),
                                    None)
                if number_index is not None:
                    trade_info['stop_loss'] = parts[number_index]
                else:
                    trade_info['stop_loss'] = float(parts[-1]) if parts[-1].replace('.', '', 1).isdigit() else 0

            return trade_info

        if close_before_match:
            trade_info['close_before'] = True
            trade_info['message_type'] = 'close'

            return trade_info

        trade_info = {
            'symbol': None,
            'direction': None,
            'entry_price': 0,
            'stop_loss': 0,
            'take_profits': [],
            'message_type': None
        }

        # Extract main data (symbol, direction, entry price)
        main_match = re.search(patterns['symbol'], message, re.IGNORECASE)
        if main_match:
            trade_info['symbol'] = main_match.group('symbol').upper()
            trade_info['direction'] = main_match.group('direction').upper()
            trade_info['entry_price'] = float(main_match.group('entry_price'))
            trade_info['message_type'] = 'create'

        # Extract stop loss
        sl_match = re.search(patterns['stop_loss'], message, re.IGNORECASE)
        if sl_match:
            trade_info['stop_loss'] = float(sl_match.group(1))

        # Extract take profits
        tp_matches = re.findall(patterns['take_profits'], message, re.IGNORECASE)
        if tp_matches:
            trade_info['take_profits'] = [float(tp) for tp in tp_matches]

        if all(value in [None, []] for value in trade_info.values()):
            return None

        logger.info(f"📨 Parsed text: {trade_info}")

        return trade_info
    except Exception as e:
        logger.error(f"❌ Error extracting trade data: {e}")
        return None


def create_trade_entries(trade_data: Dict[str, Any], message_id: str, account_config: Dict[str, Any]) -> list[
    Dict[str, Any]]:
    """Create structured trade dictionaries from extracted trade data."""
    try:
        trade_entries = []
        account_id = account_config.get('ACCOUNT')
        trade_mng = {k.upper(): v for k, v in account_config.get("TRADE_MNG", {}).items()}
        symbol_key = trade_data['symbol'].upper()
        symbol_data = trade_mng.get(trade_data['symbol'], {})
        # If no exact match, search using substring matching.
        if not symbol_data:
            symbol_data = next((v for k, v in trade_mng.items() if symbol_key in k), None)

        trade_template = {
            'symbol': symbol_data.get('symbol'),
            'lot_size': symbol_data.get('lot_size', 0),
            'n_trades': symbol_data.get('n_trades', 1),
            'direction': trade_data['direction'],
            'entry_price': trade_data['entry_price'],
            'db_message_id': message_id,
            'SL': trade_data.get('stop_loss', 0),
            'account_id': account_id
        }

        take_profits = trade_data.get('take_profits', [])
        selected_tps = take_profits[-3:] if len(take_profits) >= 6 else take_profits[-2:]

        if not selected_tps:
            trade_entries.append({**trade_template, 'TP': 0})
        else:
            trade_entries.extend([{**trade_template, 'TP': tp} for tp in selected_tps])

        return trade_entries
    except Exception as e:
        logger.error(f"❌ Error creating trade dictionaries: {e}")
        return []