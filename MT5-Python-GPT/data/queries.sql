CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    timestamp TIMESTAMP,
    text TEXT,
    processed BOOLEAN DEFAULT FALSE,
    chat_id TEXT
);
---
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    message_id INTEGER,
    asset TEXT,
    type TEXT,
    entry DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    take_profit DOUBLE PRECISION,
    status TEXT DEFAULT 'open',
    break_even DOUBLE PRECISION,
    order_id TEXT,
    volume DOUBLE PRECISION,
    account_id INTEGER,
    FOREIGN KEY (message_id) REFERENCES messages(id),
);
---
CREATE TABLE IF NOT EXISTS trade_updates (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER,
    update_text TEXT,
    new_value DOUBLE PRECISION,
    order_id TEXT,
    account_id INTEGER,
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);
---
CREATE TABLE public.software_accounts (
	mt5_account_id int4 NOT NULL,
	mt5_server text NULL,
	mt5_broker text NULL,
	mt5_balance int4 NULL,
	environment text NULL,
	telegram_id text NULL,
	telegram_phone text NULL,
	telegram_channels text NULL,
	telegram_session text NULL,
	mt5_password text NULL,
	telegram_hash text NULL,
	CONSTRAINT software_accounts_pkey PRIMARY KEY (mt5_account_id)
);