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
"""

if __name__ == "__main__":
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text(DDL))
    print("Schema applied.")
