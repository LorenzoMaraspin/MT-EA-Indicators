import json
import re
import redis
import telethon

from telethon import TelegramClient, events, sync

api_id = 26315382
api_hash = '1e5b4eb8ce692776fb096d1a863e92d8'
# channel id: -1002348864405
# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0)
client = TelegramClient('mt5listenerSession', api_id, api_hash)

# Global variable to store the parsed message
parsed_message = None

def parse_message(message):
    data = {}
    # Extract symbol, direction, and entry price
    match = re.search(r'(\w+)\s+(BUY|SELL)\s+@\s+(\d+)', message)
    if match:
        data['symbol'] = match.group(1)
        data['direction'] = match.group(2)
        data['entry_price'] = int(match.group(3))

    # Extract SL
    match = re.search(r'SL-\s*(\d+)', message)
    if match:
        data['SL'] = int(match.group(1))

    # Extract TPs
    tps = re.findall(r'TP\d+-\s*(\d+)', message)
    data['TPs'] = {f"TP{i}": int(tps[i]) for i in range(0, len(tps), 1)}

    return data

def compare_dicts(dict1, dict2):
    added = {k: dict2[k] for k in dict2 if k not in dict1}
    removed = {k: dict1[k] for k in dict1 if k not in dict2}
    modified = {k: (dict1[k], dict2[k]) for k in dict1 if k in dict2 and dict1[k] != dict2[k]}
    return added, removed, modified

@client.on(events.NewMessage)
async def handle_new_message(event):
    message_text = event.message.message
    # Global variable to store the parsed message
    parsed_message = parse_message(message_text)

    redis_client.set('telegram_message_id', event.message.id)
    redis_client.set('telegram_message_text', json.dumps(parsed_message))

    print(f"New message from {parsed_message}")


@client.on(events.MessageEdited)
async def handle_edited_message(event):
    message_id = int(redis_client.get('telegram_message_id'))
    message_text = json.loads(redis_client.get('telegram_message_text'))
    message_text_edited = event.message.message
    if message_id == event.message.id:
        date = parse_message(message_text_edited)
        added, removed, modified = compare_dicts(message_text, date)
        print(modified)

client.start()
client.run_until_disconnected()