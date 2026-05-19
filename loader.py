import argparse
from datetime import date

import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, MetaData
from sqlalchemy.dialects.postgresql import insert

from config import DB_URL, DEFAULT_START, TICKERS


def get_table(engine):
    meta = MetaData()
    meta.reflect(bind=engine, only=["prices"])
    return meta.tables["prices"]


def fetch(ticker: str, start: str, end: str) -> list[dict]:
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if df.empty:
        return []

    # reset_index first so Date becomes a regular column, then flatten MultiIndex
    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    df.columns = [c.lower() for c in df.columns]

    df["date"] = df["date"].dt.date
    df["ticker"] = ticker

    return df[["ticker", "date", "open", "high", "low", "close", "volume"]].to_dict("records")


def upsert(engine, rows: list[dict], table) -> int:
    if not rows:
        return 0
    stmt = insert(table).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker", "date"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
        },
    )
    with engine.begin() as conn:
        result = conn.execute(stmt)
    return result.rowcount


def load(tickers: list[str], start: str, end: str):
    engine = create_engine(DB_URL)
    table = get_table(engine)

    for ticker in tickers:
        print(f"  {ticker}: fetching...", end=" ", flush=True)
        rows = fetch(ticker, start, end)
        if not rows:
            print("no data.")
            continue
        affected = upsert(engine, rows, table)
        print(f"{len(rows)} rows fetched, {affected} rows upserted.")


def main():
    parser = argparse.ArgumentParser(description="Load OHLCV data into stock_pipeline")
    parser.add_argument("--tickers", nargs="+", default=TICKERS)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=str(date.today()))
    args = parser.parse_args()

    print(f"Loading {args.tickers} from {args.start} to {args.end}")
    load(args.tickers, args.start, args.end)
    print("Done.")


if __name__ == "__main__":
    main()
