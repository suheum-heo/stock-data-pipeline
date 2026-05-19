import pandas as pd
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.dialects.postgresql import insert

from config import DB_URL

WINDOW_SQL = """
WITH returns AS (
    SELECT
        ticker,
        date,
        close,
        (close - LAG(close) OVER (PARTITION BY ticker ORDER BY date))
            / LAG(close) OVER (PARTITION BY ticker ORDER BY date)  AS daily_return,
        AVG(close) OVER (PARTITION BY ticker ORDER BY date
                         ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS sma_20,
        AVG(close) OVER (PARTITION BY ticker ORDER BY date
                         ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS sma_50,
        STDDEV(close) OVER (PARTITION BY ticker ORDER BY date
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS std_20
    FROM prices
)
SELECT
    ticker,
    date,
    close,
    sma_20,
    sma_50,
    std_20,
    daily_return,
    STDDEV(daily_return) OVER (PARTITION BY ticker ORDER BY date
                                ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
        * SQRT(252) AS volatility_20,
    sma_20 + 2 * std_20 AS bb_upper,
    sma_20 - 2 * std_20 AS bb_lower
FROM returns
ORDER BY ticker, date
"""


def _add_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["daily_return"]
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    # Wilder's smoothing: ewm with com = period - 1
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    return (100 - 100 / (1 + rs)).round(2)


def _add_macd(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def compute_and_store():
    engine = create_engine(DB_URL)

    print("Running window function query...")
    with engine.connect() as conn:
        df = pd.read_sql(text(WINDOW_SQL), conn)

    df = df.dropna(subset=["daily_return"]).reset_index(drop=True)

    # EMA-based indicators computed per ticker in pandas
    parts = []
    for ticker, grp in df.groupby("ticker", sort=False):
        grp = grp.copy().sort_values("date")
        grp["rsi_14"] = _add_rsi(grp)
        grp["macd"], grp["macd_signal"] = _add_macd(grp)
        parts.append(grp)
    df = pd.concat(parts).reset_index(drop=True)

    print(f"  {len(df)} rows computed across {df['ticker'].nunique()} tickers.")

    meta = MetaData()
    meta.reflect(bind=engine, only=["metrics"])
    table = meta.tables["metrics"]

    rows = df[[
        "ticker", "date", "sma_20", "sma_50", "daily_return", "volatility_20",
        "bb_upper", "bb_lower", "rsi_14", "macd", "macd_signal",
    ]].to_dict("records")

    stmt = insert(table).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker", "date"],
        set_={c: getattr(stmt.excluded, c) for c in [
            "sma_20", "sma_50", "daily_return", "volatility_20",
            "bb_upper", "bb_lower", "rsi_14", "macd", "macd_signal",
        ]},
    )
    with engine.begin() as conn:
        conn.execute(stmt)
    print("  Upserted into metrics table.")

    latest = (
        df.sort_values("date").groupby("ticker").last().reset_index()
        [["ticker", "date", "sma_20", "sma_50", "volatility_20", "rsi_14"]]
    )
    latest.columns = ["Ticker", "Date", "SMA-20", "SMA-50", "Ann. Vol (20d)", "RSI-14"]
    latest["Ann. Vol (20d)"] = latest["Ann. Vol (20d)"].map("{:.1%}".format)
    latest["SMA-20"] = latest["SMA-20"].map("${:.2f}".format)
    latest["SMA-50"] = latest["SMA-50"].map("${:.2f}".format)
    latest["RSI-14"] = latest["RSI-14"].map("{:.1f}".format)
    print("\nLatest metrics:")
    print(latest.to_string(index=False))


if __name__ == "__main__":
    compute_and_store()
    print("\nDone.")
