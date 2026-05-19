import pandas as pd
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.dialects.postgresql import insert

from config import DB_URL

WINDOW_SQL = """
WITH returns AS (
    SELECT
        ticker,
        date,
        (close - LAG(close) OVER (PARTITION BY ticker ORDER BY date))
            / LAG(close) OVER (PARTITION BY ticker ORDER BY date)  AS daily_return,
        AVG(close) OVER (PARTITION BY ticker ORDER BY date
                         ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20,
        AVG(close) OVER (PARTITION BY ticker ORDER BY date
                         ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma_50
    FROM prices
)
SELECT
    ticker,
    date,
    sma_20,
    sma_50,
    daily_return,
    STDDEV(daily_return) OVER (PARTITION BY ticker ORDER BY date
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
        * SQRT(252) AS volatility_20
FROM returns
ORDER BY ticker, date
"""


def compute_and_store():
    engine = create_engine(DB_URL)

    print("Running window function query...")
    with engine.connect() as conn:
        df = pd.read_sql(text(WINDOW_SQL), conn)

    # Drop first row per ticker (LAG produces NULL for daily_return)
    df = df.dropna(subset=["daily_return"]).reset_index(drop=True)
    print(f"  {len(df)} rows computed across {df['ticker'].nunique()} tickers.")

    meta = MetaData()
    meta.reflect(bind=engine, only=["metrics"])
    table = meta.tables["metrics"]

    rows = df.to_dict("records")
    stmt = insert(table).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker", "date"],
        set_={
            "sma_20": stmt.excluded.sma_20,
            "sma_50": stmt.excluded.sma_50,
            "daily_return": stmt.excluded.daily_return,
            "volatility_20": stmt.excluded.volatility_20,
        },
    )
    with engine.begin() as conn:
        conn.execute(stmt)
    print(f"  Upserted into metrics table.")

    # Summary: latest values per ticker
    latest = (
        df.sort_values("date")
        .groupby("ticker")
        .last()
        .reset_index()[["ticker", "date", "sma_20", "sma_50", "volatility_20"]]
    )
    latest.columns = ["Ticker", "Date", "SMA-20", "SMA-50", "Ann. Vol (20d)"]
    latest["Ann. Vol (20d)"] = latest["Ann. Vol (20d)"].map("{:.1%}".format)
    latest["SMA-20"] = latest["SMA-20"].map("${:.2f}".format)
    latest["SMA-50"] = latest["SMA-50"].map("${:.2f}".format)
    print("\nLatest metrics:")
    print(latest.to_string(index=False))


if __name__ == "__main__":
    compute_and_store()
    print("\nDone.")
