import asyncio
import json
import logging
import redis
from typing import Dict, Any, Optional
from telethon import TelegramClient, events
from utility import read_env_vars, find_modified_properties, create_trade_dicts, parse_trade_signal
from metatraderHandler import MetatraderHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegramListener")

# Read environment variables
config = read_env_vars()

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Telegram client setup
tg_key_based_on_env = "TG_DEV" if config['ENV'] == 'DEV' else "TG_PROD"
client = TelegramClient(
    config[tg_key_based_on_env]['SESSION'],
    config[tg_key_based_on_env]['ID'],
    config[tg_key_based_on_env]['HASH'],
    timeout=10,
    retry_delay=5,
    request_retries=10
)

# MetaTrader handler
metatraderHandler = MetatraderHandler(
    config['MT5']['ACCOUNT'],
    config['MT5']['PASSWORD'],
    config['MT5']['SERVER']
)

# Destination chat ID
destination_chat_id = -1002404066652

async def handle_new_message(event: events.NewMessage.Event) -> None:
    """Handle new messages from Telegram channels."""
    message_text = event.message.message
    chat_id = event.chat_id
    parsed_message = parse_trade_signal(message_text)

    # Forward the message to the destination chat
    await client.forward_messages(destination_chat_id, event.message)

    if parsed_message is None:
        logger.error("Invalid message")
        return

    if "break_even" in parsed_message and parsed_message["break_even"]:
        trade_id = json.loads(redis_client.get(f'{chat_id}_{event.message.id}_trades_id'))
        metatraderHandler.update_trade(trade_id)
    else:
        trades_dict = create_trade_dicts(parsed_message, config)
        redis_client.set(f'{chat_id}_{event.message.id}_message_id', event.message.id)
        redis_client.set(f'{chat_id}_{event.message.id}_message_text', json.dumps(parsed_message))
        trade_ids = metatraderHandler.open_multiple_trades(
            trades_dict,
            config['MT5']['TRADE_MANAGEMENT'][parsed_message['symbol']]['default_trades']
        )
        redis_client.set(f'{chat_id}_{event.message.id}_trades_id', json.dumps(trade_ids))

async def handle_edited_message(event: events.MessageEdited.Event) -> None:
    """Handle edited messages from Telegram channels."""
    message_id = event.message.id
    message_text = event.message.message
    chat_id = event.chat_id

    cache_message_id = int(redis_client.get(f'{chat_id}_{message_id}_message_id'))
    cache_message_text = json.loads(redis_client.get(f'{chat_id}_{message_id}_message_text'))

    if cache_message_id == event.message.id and cache_message_text is not None and message_text != cache_message_text:
        parsed_message = parse_trade_signal(message_text)
        modified = find_modified_properties(parsed_message, message_text)

        if modified:
            logger.info(f"Modified properties: {modified}")
            sl = modified['SL'][0] if 'SL' in modified else None
            tps = {key: value[0] for key, value in modified['TPs'].items()} if 'TPs' in modified else None
            trade_id = json.loads(redis_client.get(f'{chat_id}_{message_id}_trades_id'))
            metatraderHandler.update_trade(trade_id, new_sl=sl, new_tps=tps)
            redis_client.set(f'{chat_id}_{event.message.id}_message_text', json.dumps(parsed_message))
        else:
            logger.info("No modified properties")

async def get_all_chats() -> None:
    """Retrieve and print all chats."""
    dialogs = await client.get_dialogs()
    for dialog in dialogs:
        logger.info(f"Chat Name: {dialog.name}, Chat ID: {dialog.id}")

async def get_channel_history(channel_id: int, limit: int = 100) -> str:
    """Retrieve message history from a channel."""
    messages = await client.get_messages(channel_id, limit=limit)
    messages_dict = {index + 1: message.text.strip() for index, message in enumerate(messages)}
    return json.dumps({"messages": messages_dict, "count": len(messages_dict)})

async def keep_alive() -> None:
    """Ensure the client stays connected."""
    while True:
        if not client.is_connected():
            logger.warning("Client disconnected, attempting to reconnect...")
            await client.connect()
        await asyncio.sleep(30)

async def main() -> None:
    """Main function to run the Telegram listener."""
    while True:
        try:
            await client.connect()
            if not await client.is_user_authorized():
                await client.send_code_request(config[tg_key_based_on_env]['PHONE'])
                await client.sign_in(config[tg_key_based_on_env]['PHONE'], input("Enter the code: "))

            logger.info("Bot started!")
            await client.run_until_disconnected()
        except (ConnectionError, asyncio.TimeoutError, OSError) as e:
            logger.warning(f"Connection error: {e}, restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    with client:
        client.start()
        client.loop.create_task(keep_alive())
        client.loop.run_until_complete(main())