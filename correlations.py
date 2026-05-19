import pandas as pd
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.dialects.postgresql import insert

from config import DB_URL

WINDOW = 30  # trading days


def compute_and_store():
    engine = create_engine(DB_URL)

    print("Loading daily returns...")
    with engine.connect() as conn:
        df = pd.read_sql(
            text("SELECT ticker, date, daily_return FROM metrics ORDER BY date"),
            conn, parse_dates=["date"],
        )

    # Pivot to wide: rows=date, cols=ticker
    wide = df.pivot(index="date", columns="ticker", values="daily_return").sort_index()

    print(f"  Computing rolling {WINDOW}-day correlations...")
    records = []
    dates = wide.index[WINDOW - 1:]  # first valid window ends here
    tickers = wide.columns.tolist()

    for date in dates:
        window_data = wide.loc[:date].iloc[-WINDOW:]
        corr_matrix = window_data.corr()
        for i, ta in enumerate(tickers):
            for tb in tickers[i + 1:]:  # upper triangle only, no self-pairs
                val = corr_matrix.loc[ta, tb]
                if pd.notna(val):
                    records.append({"date": date.date(), "ticker_a": ta, "ticker_b": tb, "correlation": round(float(val), 4)})

    print(f"  {len(records)} correlation pairs computed.")

    meta = MetaData()
    meta.reflect(bind=engine, only=["correlations"])
    table = meta.tables["correlations"]

    stmt = insert(table).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["date", "ticker_a", "ticker_b"],
        set_={"correlation": stmt.excluded.correlation},
    )
    with engine.begin() as conn:
        conn.execute(stmt)
    print("  Upserted into correlations table.")

    # Print latest correlation matrix
    latest_date = max(r["date"] for r in records)
    latest = {(r["ticker_a"], r["ticker_b"]): r["correlation"]
              for r in records if r["date"] == latest_date}
    print(f"\nLatest correlations ({latest_date}):")
    header = f"{'':6}" + "".join(f"{t:>7}" for t in tickers)
    print(header)
    for ta in tickers:
        row = f"{ta:6}"
        for tb in tickers:
            if ta == tb:
                row += f"{'1.00':>7}"
            elif (ta, tb) in latest:
                row += f"{latest[(ta, tb)]:>7.2f}"
            else:
                row += f"{latest.get((tb, ta), float('nan')):>7.2f}"
        print(row)


if __name__ == "__main__":
    compute_and_store()
    print("\nDone.")
