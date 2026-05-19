import os
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from config import DB_URL

load_dotenv()

VOLATILITY_THRESHOLD = 0.50  # 50% annualized


def check_and_alert():
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("  SLACK_WEBHOOK_URL not set — skipping alert.")
        return

    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT ON (ticker) ticker, date, volatility_20, rsi_14
            FROM metrics
            ORDER BY ticker, date DESC
        """)).fetchall()

    spikes = [r for r in rows if r.volatility_20 and r.volatility_20 > VOLATILITY_THRESHOLD]

    if not spikes:
        print("  All tickers below volatility threshold — no alert sent.")
        return

    lines = [f"*Volatility Spike Alert* — {spikes[0].date}"]
    for r in spikes:
        lines.append(f"• *{r.ticker}*: vol={r.volatility_20:.1%}  RSI={r.rsi_14:.1f}")

    payload = {"text": "\n".join(lines)}
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    print(f"  Alert sent for: {[r.ticker for r in spikes]}")


if __name__ == "__main__":
    check_and_alert()
    print("Done.")
