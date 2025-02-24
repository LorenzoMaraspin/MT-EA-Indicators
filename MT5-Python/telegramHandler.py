import asyncio
import json
import logging
import redis
from typing import Dict, Any, Optional
from telethon import TelegramClient, events
from metatraderHandler import MetatraderHandler
from utility import read_env_vars, find_modified_properties, create_trade_dicts, parse_trade_signal

logger = logging.getLogger("telegramListener")

class TelegramHandler:
    def __init__(self, config: Dict[str, Any], metatraderHandler: MetatraderHandler):
        """Initialize the Telegram handler."""
        self.config = config
        self.metatraderHandler = metatraderHandler
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.destination_chat_id = -1002404066652

        # Telegram client setup
        self.tg_key_based_on_env = "TG_DEV" if config['ENV'] == 'DEV' else "TG_PROD"
        self.client = TelegramClient(
            config[self.tg_key_based_on_env]['SESSION'],
            config[self.tg_key_based_on_env]['ID'],
            config[self.tg_key_based_on_env]['HASH'],
            timeout=10,
            retry_delay=5,
            request_retries=10
        )

        # Register event handlers
        self.client.on(events.NewMessage(chats=config[self.tg_key_based_on_env]['CHANNELS']))(self.handle_new_message)
        self.client.on(events.MessageEdited(chats=config[self.tg_key_based_on_env]['CHANNELS']))(self.handle_edited_message)

    async def handle_new_message(self, event: events.NewMessage.Event) -> None:
        """Handle new messages from Telegram channels."""
        message_text = event.message.message
        chat_id = event.chat_id
        parsed_message = parse_trade_signal(message_text)

        # Forward the message to the destination chat
        await self.client.forward_messages(self.destination_chat_id, event.message)

        if parsed_message is None:
            logger.error("Invalid message")
            return

        if "break_even" in parsed_message and parsed_message["break_even"]:
            trade_id = json.loads(self.redis_client.get(f'{chat_id}_{event.message.id}_trades_id'))
            self.metatraderHandler.update_trade(trade_id)
        else:
            trades_dict = create_trade_dicts(parsed_message, self.config)
            self.redis_client.set(f'{chat_id}_{event.message.id}_message_id', event.message.id)
            self.redis_client.set(f'{chat_id}_{event.message.id}_message_text', json.dumps(parsed_message))
            trade_ids = self.metatraderHandler.open_multiple_trades(
                trades_dict,
                self.config['MT5']['TRADE_MANAGEMENT'][parsed_message['symbol']]['default_trades']
            )
            self.redis_client.set(f'{chat_id}_{event.message.id}_trades_id', json.dumps(trade_ids))

    async def handle_edited_message(self, event: events.MessageEdited.Event) -> None:
        """Handle edited messages from Telegram channels."""
        message_id = event.message.id
        message_text = event.message.message
        chat_id = event.chat_id

        cache_message_id = int(self.redis_client.get(f'{chat_id}_{message_id}_message_id'))
        cache_message_text = json.loads(self.redis_client.get(f'{chat_id}_{message_id}_message_text'))

        if cache_message_id == event.message.id and cache_message_text is not None and message_text != cache_message_text:
            parsed_message = parse_trade_signal(message_text)
            modified = find_modified_properties(parsed_message, cache_message_text)

            if modified:
                logger.info(f"Modified properties: {modified}")
                sl = modified['stop_loss'][0] if 'stop_loss' in modified else None
                tps = {key: value[0] for key, value in modified['take_profits'].items()} if 'take_profits' in modified else None
                trade_id = json.loads(self.redis_client.get(f'{chat_id}_{message_id}_trades_id'))
                self.metatraderHandler.update_trade(trade_id, new_sl=sl, new_tps=tps)
                self.redis_client.set(f'{chat_id}_{event.message.id}_message_text', json.dumps(parsed_message))
            else:
                logger.info("No modified properties")

    async def get_all_chats(self) -> None:
        """Retrieve and print all chats."""
        dialogs = await self.client.get_dialogs()
        for dialog in dialogs:
            logger.info(f"Chat Name: {dialog.name}, Chat ID: {dialog.id}")

    async def get_channel_history(self, channel_id: int, limit: int = 100) -> str:
        """Retrieve message history from a channel."""
        messages = await self.client.get_messages(channel_id, limit=limit)
        messages_dict = {index + 1: message.text.strip() for index, message in enumerate(messages)}
        return json.dumps({"messages": messages_dict, "count": len(messages_dict)})

    async def keep_alive(self) -> None:
        """Ensure the client stays connected."""
        while True:
            if not self.client.is_connected():
                logger.warning("Client disconnected, attempting to reconnect...")
                await self.client.connect()
            await asyncio.sleep(30)

    async def start(self) -> None:
        """Start the Telegram client."""
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.config[self.tg_key_based_on_env]['PHONE'])
            await self.client.sign_in(self.config[self.tg_key_based_on_env]['PHONE'], input("Enter the code: "))
        logger.info("Telegram client started!")
        await self.client.run_until_disconnected()