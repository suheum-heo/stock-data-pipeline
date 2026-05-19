import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/stock_pipeline")

TICKERS = ["SPY", "QQQ", "AAPL", "TSLA", "VTI", "NVDA", "MSFT", "GLD"]

DEFAULT_START = "2020-01-01"
