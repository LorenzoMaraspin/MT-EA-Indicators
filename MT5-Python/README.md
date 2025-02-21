# Project Overview

This project integrates Telegram with MetaTrader 5 (MT5) to automate trading based on signals received via Telegram messages. The system listens for new messages and message edits in specified Telegram channels, parses the messages to extract trading signals, and executes trades on the MT5 platform accordingly. The project also includes functionality to update trades based on edited messages.

## File Descriptions

### `utility.py`

This file contains utility functions used throughout the project.

- **`read_env_vars`**: Reads environment variables and returns a configuration dictionary containing MT5 and Telegram settings.
- **`initialize_logger`**: Initializes the logger for the project.
- **`parse_trade_signal`**: Parses a trade signal from a given text message, extracting the symbol, direction, entry price, stop loss, and take profits.
- **`parse_message`**: Parses a Telegram message to extract trading information such as symbol, direction, entry price, stop loss, and take profits.
- **`find_modified_properties`**: Compares two dictionaries and returns the properties that have been modified.
- **`create_trade_dicts`**: Creates trade dictionaries based on the parsed trade information and configuration settings.

### `telegramHandler.py`

This file handles interactions with Telegram and Redis, and coordinates the trading actions with MetaTrader 5.

- **`handle_new_message`**: Event handler for new messages in specified Telegram channels. Parses the message, forwards it to a destination channel, and opens trades based on the parsed information.
- **`handle_edited_message`**: Event handler for edited messages in specified Telegram channels. Checks for modifications in the message, updates trades accordingly, and updates the stored message in Redis.
- **`get_all_chats`**: Retrieves and prints all chat dialogs the Telegram client is part of.
- **`get_channel_history`**: Retrieves the message history of a specified Telegram channel.

### `metatraderHandler.py`

This file contains the `MetatraderHandler` class, which manages interactions with the MetaTrader 5 platform.

- **`__init__`**: Initializes the handler with account credentials and server information.
- **`initialize_mt5`**: Initializes the MT5 connection and logs in to the account.
- **`shutdown_mt5`**: Shuts down the MT5 connection.
- **`open_multiple_trades`**: Opens multiple trades based on the provided trade details and minimum trade count.
- **`preparation_trade`**: Prepares the trade request by determining the order type and price based on the trade direction.
- **`open_trade`**: Sends a trade request to MT5 and logs the result.
- **`update_trade`**: Updates the stop loss and take profit values for existing trades.
- **`get_account_balance`**: Retrieves and returns the account balance from MT5.

## Functionality

1. **Environment Configuration**: The project reads configuration settings from environment variables, including MT5 account details and Telegram API credentials.
2. **Telegram Message Handling**: The system listens for new messages and message edits in specified Telegram channels. It parses these messages to extract trading signals.
3. **Trade Execution**: Based on the parsed trading signals, the system opens trades on the MT5 platform. It also updates trades if the corresponding Telegram message is edited.
4. **Logging and Error Handling**: The project includes comprehensive logging and error handling to ensure smooth operation and easy debugging.
5. **Redis Integration**: The project uses Redis to store and retrieve message and trade information, ensuring consistency and enabling updates based on message edits.

## Fixes to Implement

1. Accept poorly formatted messages like "Xau buy 2354" where "XAUUSD" is not written and "@" is missing.
2. After sending the above poorly formatted message, the position was not opened and thus not written to Redis. Subsequently, the message was edited, but the edit function did not work because it did not find the message in Redis. Therefore, when checking if it already exists, it resulted in an error. Even though the message was eventually edited as expected, it still failed to open the position. Additional checks are needed.