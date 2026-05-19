import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from config import TICKERS

load_dotenv()

st.set_page_config(page_title="Stock Pipeline Dashboard", layout="wide")


def _db_url() -> str:
    # Streamlit Cloud injects secrets; fall back to .env / local for dev
    if "DATABASE_URL" in st.secrets:
        return st.secrets["DATABASE_URL"]
    return os.getenv("DATABASE_URL", "postgresql://localhost/stock_pipeline")


@st.cache_resource
def get_engine():
    return create_engine(_db_url())

@st.cache_data(ttl=3600)
def load_prices():
    with get_engine().connect() as conn:
        return pd.read_sql(text("SELECT ticker, date, close FROM prices ORDER BY date"), conn, parse_dates=["date"])

@st.cache_data(ttl=3600)
def load_metrics():
    with get_engine().connect() as conn:
        return pd.read_sql(text("SELECT * FROM metrics ORDER BY date"), conn, parse_dates=["date"])

@st.cache_data(ttl=3600)
def load_correlations():
    with get_engine().connect() as conn:
        return pd.read_sql(text("SELECT * FROM correlations"), conn, parse_dates=["date"])


# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.title("Stock Pipeline")
selected_ticker = st.sidebar.selectbox("Ticker (Price chart)", TICKERS, index=0)

prices = load_prices()
metrics = load_metrics()
correlations = load_correlations()

date_min = prices["date"].min().date()
date_max = prices["date"].max().date()
date_range = st.sidebar.slider("Date range", min_value=date_min, max_value=date_max,
                                value=(date_min, date_max))
start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["Price + SMA", "Volatility", "Correlations", "Metrics Table"])

# Tab 1: Price + SMA
with tab1:
    st.subheader(f"{selected_ticker} — Price & Moving Averages")
    p = prices[(prices["ticker"] == selected_ticker) & (prices["date"].between(start, end))]
    m = metrics[(metrics["ticker"] == selected_ticker) & (metrics["date"].between(start, end))]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=p["date"], y=p["close"], name="Close",
                             line=dict(color="#aaaaaa", width=1)))
    fig.add_trace(go.Scatter(x=m["date"], y=m["sma_20"], name="SMA-20",
                             line=dict(color="#1f77b4", width=2)))
    fig.add_trace(go.Scatter(x=m["date"], y=m["sma_50"], name="SMA-50",
                             line=dict(color="#ff7f0e", width=2)))
    fig.add_trace(go.Scatter(x=m["date"], y=m["bb_upper"], name="BB Upper",
                             line=dict(color="#2ca02c", width=1, dash="dot")))
    fig.add_trace(go.Scatter(x=m["date"], y=m["bb_lower"], name="BB Lower",
                             line=dict(color="#2ca02c", width=1, dash="dot"),
                             fill="tonexty", fillcolor="rgba(44,160,44,0.05)"))
    fig.update_layout(xaxis_title="Date", yaxis_title="Price (USD)", hovermode="x unified", height=500)
    st.plotly_chart(fig, use_container_width=True)

# Tab 2: Volatility
with tab2:
    st.subheader("Current Annualized Volatility (20-day)")
    latest_vol = (
        metrics.sort_values("date").groupby("ticker").last().reset_index()
        [["ticker", "volatility_20"]]
    )
    latest_vol["color"] = latest_vol["volatility_20"].apply(
        lambda v: "#d62728" if v > 0.50 else "#1f77b4"
    )
    latest_vol = latest_vol.sort_values("volatility_20", ascending=False)

    fig2 = go.Figure(go.Bar(
        x=latest_vol["ticker"], y=latest_vol["volatility_20"],
        marker_color=latest_vol["color"],
        text=latest_vol["volatility_20"].map("{:.1%}".format),
        textposition="outside",
    ))
    fig2.add_hline(y=0.50, line_dash="dash", line_color="red",
                   annotation_text="50% threshold", annotation_position="top right")
    fig2.update_layout(yaxis_tickformat=".0%", yaxis_title="Annualized Volatility",
                       xaxis_title="Ticker", height=450)
    st.plotly_chart(fig2, use_container_width=True)

# Tab 3: Correlation Heatmap
with tab3:
    st.subheader("Rolling 30-Day Return Correlations (latest)")
    latest_date = correlations["date"].max()
    latest_corr = correlations[correlations["date"] == latest_date]

    # Build symmetric matrix
    tickers_sorted = sorted(TICKERS)
    matrix = pd.DataFrame(1.0, index=tickers_sorted, columns=tickers_sorted)
    for _, row in latest_corr.iterrows():
        matrix.loc[row["ticker_a"], row["ticker_b"]] = row["correlation"]
        matrix.loc[row["ticker_b"], row["ticker_a"]] = row["correlation"]

    fig3 = px.imshow(matrix, color_continuous_scale="RdBu", zmin=-1, zmax=1,
                     text_auto=".2f", aspect="auto")
    fig3.update_layout(height=500,
                       title=f"Correlation matrix as of {latest_date.date()}")
    st.plotly_chart(fig3, use_container_width=True)

# Tab 4: Metrics Table
with tab4:
    st.subheader("Latest Metrics — All Tickers")
    table_df = (
        metrics.sort_values("date").groupby("ticker").last().reset_index()
        [["ticker", "date", "sma_20", "sma_50", "volatility_20", "rsi_14", "macd", "macd_signal", "bb_upper", "bb_lower"]]
        .sort_values("ticker")
    )
    table_df.columns = ["Ticker", "Date", "SMA-20", "SMA-50", "Vol (ann.)", "RSI-14",
                         "MACD", "MACD Signal", "BB Upper", "BB Lower"]
    table_df["Vol (ann.)"] = table_df["Vol (ann.)"].map("{:.1%}".format)
    st.dataframe(table_df, use_container_width=True, hide_index=True)
