import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from sqlalchemy import create_engine, text

from config import DB_URL, TICKERS

CHARTS_DIR = Path(__file__).parent / "charts"


def load_data(engine, ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = pd.read_sql(
        text("SELECT date, close FROM prices WHERE ticker = :t ORDER BY date"),
        engine, params={"t": ticker}, parse_dates=["date"],
    )
    metrics = pd.read_sql(
        text("SELECT date, sma_20, sma_50, volatility_20 FROM metrics WHERE ticker = :t ORDER BY date"),
        engine, params={"t": ticker}, parse_dates=["date"],
    )
    return prices, metrics


def plot_ticker(ticker: str, prices: pd.DataFrame, metrics: pd.DataFrame):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})
    fig.suptitle(f"{ticker} — Price & Moving Averages", fontsize=14, fontweight="bold")

    # Top: price + SMAs
    ax1.plot(prices["date"], prices["close"], color="#aaaaaa", linewidth=0.8, label="Close")
    ax1.plot(metrics["date"], metrics["sma_20"], color="#1f77b4", linewidth=1.5, label="SMA-20")
    ax1.plot(metrics["date"], metrics["sma_50"], color="#ff7f0e", linewidth=1.5, label="SMA-50")
    ax1.set_ylabel("Price (USD)")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Bottom: annualized volatility
    median_vol = metrics["volatility_20"].median()
    ax2.plot(metrics["date"], metrics["volatility_20"], color="#d62728", linewidth=1.2, label="20d Vol (ann.)")
    ax2.axhline(median_vol, color="#d62728", linestyle="--", linewidth=0.8, alpha=0.6,
                label=f"Median {median_vol:.1%}")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax2.set_ylabel("Volatility")
    ax2.set_xlabel("Date")
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-show", action="store_true", help="Skip plt.show() for headless runs")
    args = parser.parse_args()

    CHARTS_DIR.mkdir(exist_ok=True)
    engine = create_engine(DB_URL)

    for ticker in TICKERS:
        print(f"  Plotting {ticker}...", end=" ", flush=True)
        prices, metrics = load_data(engine, ticker)
        fig = plot_ticker(ticker, prices, metrics)
        out = CHARTS_DIR / f"{ticker}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"saved → {out.name}")

    if not args.no_show:
        # Re-open saved PNGs for interactive display
        for ticker in TICKERS:
            img = plt.imread(CHARTS_DIR / f"{ticker}.png")
            fig, ax = plt.subplots(figsize=(14, 8))
            ax.imshow(img)
            ax.axis("off")
            fig.suptitle(ticker)
        plt.show()


if __name__ == "__main__":
    main()
