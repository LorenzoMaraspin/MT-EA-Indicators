CREATE TABLE IF NOT EXISTS tg_message (
    msg_id SERIAL PRIMARY KEY,
    tg_msg_id INTEGER,
    tg_chat_id TEXT,
    tg_src_chat_name TEXT,
    tg_dst_chat_id TEXT,
    tg_dst_msg_id INTEGER,
    msg_body TEXT,
    msg_timestamp TIMESTAMP,
    msg_status TEXT
);
---
CREATE TABLE IF NOT EXISTS trade (
    trade_id SERIAL PRIMARY KEY,
    msg_id INTEGER,
    order_id INTEGER,
    account_id INTEGER,
    symbol TEXT,
    direction TEXT,
    entry_price DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    take_profit DOUBLE PRECISION,
    break_even DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    status TEXT DEFAULT 'open',
    FOREIGN KEY (msg_id) REFERENCES tg_message(msg_id),
);
---
CREATE TABLE IF NOT EXISTS tradeUpdate (
    trade_update_id SERIAL PRIMARY KEY,
    trade_id INTEGER,
    order_id INTEGER,
    account_id INTEGER,
    update_action TEXT,
    update_body TEXT
    FOREIGN KEY (trade_id) REFERENCES trade(trade_id)
);
---
CREATE TABLE IF NOT EXISTS account (
	mt5_account_id INTEGER PRIMARY KEY,
	mt5_server TEXT,
	mt5_broker TEXT,
	mt5_balance DOUBLE PRECISION,
	mt5_password TEXT,
	environment TEXT,
	tg_id TEXT,
	tg_phone TEXT,
	tg_channels TEXT,
	tg_session TEXT,
	tg_hash TEXT
);
---
CREATE TABLE IF NOT EXISTS broker_config (
    id SERIAL PRIMARY KEY,
    account_id INTEGER,
    broker_name TEXT,
    FOREIGN KEY (account_id) REFERENCES account(mt5_account_id)
);

---
CREATE TABLE IF NOT EXISTS broker_symbol_config (
    id SERIAL PRIMARY KEY,
    broker_config_id INTEGER,
    instrument TEXT, -- es. "XAUUSD", "US30"
    symbol TEXT,     -- es. "XAUUSD+", "DJ30"
    n_trades INTEGER,
    lot_size DOUBLE PRECISION,
    FOREIGN KEY (broker_config_id) REFERENCES broker_config(id)
);