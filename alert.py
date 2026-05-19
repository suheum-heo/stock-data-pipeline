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

    rows = sorted(rows, key=lambda r: r.volatility_20 or 0, reverse=True)
    spikes = [r for r in rows if r.volatility_20 and r.volatility_20 > VOLATILITY_THRESHOLD]
    report_date = rows[0].date if rows else "N/A"

    lines = [f"*Daily Market Summary* — {report_date}"]

    if spikes:
        lines.append(f"\n:rotating_light: *Volatility Spike* (>{VOLATILITY_THRESHOLD:.0%})")
        for r in spikes:
            lines.append(f"  • *{r.ticker}*: vol={r.volatility_20:.1%}  RSI={r.rsi_14:.1f}")

    lines.append("\n*Volatility Rankings (20d ann.)*")
    for r in rows:
        bar = "█" * int((r.volatility_20 or 0) * 20)
        flag = " :rotating_light:" if r.volatility_20 and r.volatility_20 > VOLATILITY_THRESHOLD else ""
        lines.append(f"  {r.ticker:<5} {r.volatility_20:.1%}  {bar}{flag}")

    payload = {"text": "\n".join(lines)}
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    print(f"  Summary sent. Spikes: {[r.ticker for r in spikes] or 'none'}")


if __name__ == "__main__":
    check_and_alert()
    print("Done.")
