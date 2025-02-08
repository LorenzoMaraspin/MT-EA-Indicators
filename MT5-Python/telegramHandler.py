import json
import redis
from utility import read_env_vars, parse_message, find_modified_properties, create_trade_dicts
from telethon import TelegramClient, events, sync
from metatraderHandler import MetatraderHandler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegramListener")

# Read environment variables
config = read_env_vars()
# channel id: -1002348864405
# destination channel id: -1002404066652
# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0)
client = TelegramClient('mt5listenerSession', config['TG']['ID'], config['TG']['HASH'])
metatraderHandler = MetatraderHandler(config['MT5']['ACCOUNT'], config['MT5']['PASSWORD'], config['MT5']['SERVER'])
destination_chat_id = -1002404066652
# Global variable to store the parsed message

@client.on(events.NewMessage(chats=[-1002348864405]))
async def handle_new_message(event):
    message_text = event.message.message
    chat_id = event.chat_id
    parsed_message = parse_message(message_text)
    await client.forward_messages(destination_chat_id, event.message)
    if parsed_message is not None:
        if "BE" in parsed_message and parsed_message["BE"]:
            metatraderHandler.update_trade(json.loads(redis_client.get(f'{chat_id}_trades_id')))
        else:
            trades_dict = create_trade_dicts(parsed_message, config['MT5']['TP_MANAGEMENT'],
                                             config['MT5']['VANTAGE_SYMBOL_MAP'])
            redis_client.set(f'{chat_id}_message_id', event.message.id)
            redis_client.set(f'{chat_id}_message_text', json.dumps(parsed_message))
            redis_client.set(f'{chat_id}_trades_id',json.dumps(metatraderHandler.open_multiple_trades(trades_dict)))
    else:
        logger.error("Invalid message")


@client.on(events.MessageEdited(chats=[-1002348864405]))
async def handle_edited_message(event):
    chat_id = event.chat_id
    message_id = int(redis_client.get(f'{chat_id}_message_id'))
    message_text = json.loads(redis_client.get(f'{chat_id}_message_text'))
    message_text_edited = event.message.message
    if (message_id == event.message.id) and (message_text is not None) and (message_text_edited != message_text):
        date = parse_message(message_text_edited)
        modified = find_modified_properties(date, message_text)
        logger.info(f"Modified properties: {modified}")


client.start()
client.run_until_disconnected()