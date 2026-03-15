import os
from dotenv import load_dotenv

load_dotenv()

# Trading pairs
PAIRS = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT"]

# Timeframes
ENTRY_TIMEFRAME = "5m"
TREND_TIMEFRAME = "1h"

# Risk management
MAX_POSITIONS = 3
RISK_PER_TRADE = 0.02  # 2%

# API keys (set in Railway Variables)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Paths – ensure these directories exist
DATA_PATH = "/app/data/"
MODEL_PATH = "/app/data/models/"  # inside the volume
