import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Pull data from Yahoo Finance
print("Fetching SPY data...")
df = yf.download("SPY", start="2023-01-01", end="2023-12-31", progress=False)
print(df.head())
print(f"\nShape: {df.shape}")

# 2. Test PostgreSQL connection
print("\nTesting PostgreSQL connection...")
engine = create_engine("postgresql://localhost/stock_pipeline")
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(result.fetchone()[0])

print("\nSetup OK")
