import json
import re
import redis
import telethon
from utility import read_env_vars, parse_message, find_modified_properties, create_trade_dicts
from telethon import TelegramClient, events, sync
from metatraderHandler import MetatraderHandler

# Read environment variables
config = read_env_vars()
# channel id: -1002348864405
# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0)
client = TelegramClient('mt5listenerSession', config['TG']['ID'], config['TG']['HASH'])
metatraderHandler = MetatraderHandler(config['MT5']['ACCOUNT'], config['MT5']['PASSWORD'], config['MT5']['SERVER'])

# Global variable to store the parsed message
parsed_message = None


@client.on(events.NewMessage)
async def handle_new_message(event):
    message_text = event.message.message
    # Global variable to store the parsed message
    trades_dict = create_trade_dicts(message_text, config['MT5']['TP_MANAGEMENT'], config['MT5']['VANTAGE_SYMBOL_MAP'])

    redis_client.set('telegram_message_id', event.message.id)
    redis_client.set('telegram_message_text', json.dumps(parsed_message))

    results = metatraderHandler.open_multiple_trades(trades_dict)


@client.on(events.MessageEdited)
async def handle_edited_message(event):
    message_id = int(redis_client.get('telegram_message_id'))
    message_text = json.loads(redis_client.get('telegram_message_text'))
    message_text_edited = event.message.message
    if message_id == event.message.id:
        date = parse_message(message_text_edited)
        modified = find_modified_properties(message_text, date)
        print(modified)

client.start()
client.run_until_disconnected()