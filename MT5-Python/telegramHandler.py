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
# channel id test environment: -1002348864405
# channel id prod environment: -1001426601424, -1001467277459
# destination channel id: -1002404066652
# Redis connection
tg_key_based_on_env = "TG_DEV" if config['ENV'] == 'DEV' else "TG_PROD"
redis_client = redis.Redis(host='localhost', port=6379, db=0)
client = TelegramClient(config[tg_key_based_on_env]['SESSION'], config[tg_key_based_on_env]['ID'], config[tg_key_based_on_env]['HASH'])
metatraderHandler = MetatraderHandler(config['MT5']['ACCOUNT'], config['MT5']['PASSWORD'], config['MT5']['SERVER'])
destination_chat_id = -1002404066652
# Global variable to store the parsed message

@client.on(events.NewMessage(chats=config[tg_key_based_on_env]['CHANNELS']))
async def handle_new_message(event):
    message_text = event.message.message
    chat_id = event.chat_id
    parsed_message = parse_message(message_text)
    await client.forward_messages(destination_chat_id, event.message)
    if parsed_message is not None:
        if "BE" in parsed_message and parsed_message["BE"]:
            metatraderHandler.update_trade(json.loads(redis_client.get(f'{chat_id}_{event.message.id}_trades_id')))
        else:
            trades_dict = create_trade_dicts(parsed_message, config)
            redis_client.set(f'{chat_id}_{event.message.id}_message_id', event.message.id)
            redis_client.set(f'{chat_id}_{event.message.id}_message_text', json.dumps(parsed_message))
            redis_client.set(f'{chat_id}_{event.message.id}_trades_id',json.dumps(metatraderHandler.open_multiple_trades(trades_dict,config['MT5']['TRADE_MANAGEMENT'][parsed_message['symbol']]['default_trades'])))
    else:
        logger.error("Invalid message")


@client.on(events.MessageEdited(chats=config[tg_key_based_on_env]['CHANNELS']))
async def handle_edited_message(event):
    message_id = event.message.id
    chat_id = event.chat_id
    message_id = int(redis_client.get(f'{chat_id}_{message_id}_message_id'))
    message_text = json.loads(redis_client.get(f'{chat_id}_{message_id}_message_text'))
    message_text_edited = event.message.message
    if (message_id == event.message.id) and (message_text is not None) and (message_text_edited != message_text):
        parsed_message = parse_message(message_text_edited)
        modified = find_modified_properties(parsed_message, message_text)
        if modified:
            logger.info(f"Modified properties: {modified}")
            sl = modified['SL'][0] if 'SL' in modified else None
            tps =  {key: value[0] for key, value in modified['TPs'].items()} if 'TPs' in modified else None
            metatraderHandler.update_trade(json.loads(redis_client.get(f'{chat_id}_{message_id}_trades_id')), new_sl=sl, new_tps=tps)
            redis_client.set(f'{chat_id}_{event.message.id}_message_text', json.dumps(parsed_message))
        else:
            logger.info("No modified properties")

async def get_all_chats():
    # Get all dialogs (chats)
    dialogs = await client.get_dialogs()

    # Print chat names and IDs
    for dialog in dialogs:
        print(f"Chat Name: {dialog.name}, Chat ID: {dialog.id}")

async def get_channel_history(channel_id, limit=100):
    # Get the message history
    messages = await client.get_messages(channel_id, limit=limit)
    messages_dict = {index + 1: message.text.strip() for index, message in enumerate(messages)}
    messages_count = len(messages_dict)
    return json.dumps({"messages": messages_dict, "count": messages_count})

# Run the function
client.start()

client.run_until_disconnected()