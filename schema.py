from sqlalchemy import create_engine, text
from config import DB_URL

DDL = """
CREATE TABLE IF NOT EXISTS prices (
    id         SERIAL PRIMARY KEY,
    ticker     VARCHAR(10)  NOT NULL,
    date       DATE         NOT NULL,
    open       NUMERIC(12,4),
    high       NUMERIC(12,4),
    low        NUMERIC(12,4),
    close      NUMERIC(12,4),
    volume     BIGINT,
    created_at TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_prices_ticker_date ON prices (ticker, date);

CREATE TABLE IF NOT EXISTS metrics (
    id              SERIAL PRIMARY KEY,
    ticker          VARCHAR(10)  NOT NULL,
    date            DATE         NOT NULL,
    sma_20          NUMERIC(12,4),
    sma_50          NUMERIC(12,4),
    daily_return    NUMERIC(10,6),
    volatility_20   NUMERIC(10,6),
    UNIQUE (ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_metrics_ticker_date ON metrics (ticker, date);

ALTER TABLE metrics ADD COLUMN IF NOT EXISTS rsi_14      NUMERIC(6,2);
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS bb_upper    NUMERIC(12,4);
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS bb_lower    NUMERIC(12,4);
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS macd        NUMERIC(10,6);
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS macd_signal NUMERIC(10,6);

CREATE TABLE IF NOT EXISTS correlations (
    date        DATE        NOT NULL,
    ticker_a    VARCHAR(10) NOT NULL,
    ticker_b    VARCHAR(10) NOT NULL,
    correlation NUMERIC(6,4),
    PRIMARY KEY (date, ticker_a, ticker_b)
);
"""

if __name__ == "__main__":
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text(DDL))
    print("Schema applied.")
