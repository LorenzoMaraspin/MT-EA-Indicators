CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    telegram_id INTEGER UNIQUE,
    timestamp TIMESTAMP,
    text TEXT,
    processed BOOLEAN DEFAULT FALSE
);
---
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    message_id INTEGER,
    order_id TEXT,
    asset TEXT,
    type TEXT,
    entry DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    take_profits DOUBLE PRECISION,
    break_even DOUBLE PRECISION,
    status TEXT DEFAULT 'open',
    FOREIGN KEY (message_id) REFERENCES messages(id)
);
---
CREATE TABLE IF NOT EXISTS trade_updates (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER,
    update_text TEXT,
    new_value DOUBLE PRECISION,
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);