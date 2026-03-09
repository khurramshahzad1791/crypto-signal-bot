# config.py
import os

# Trading pairs
PAIRS = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT"]

# Timeframes (in minutes)
ENTRY_TIMEFRAME = "5m"
TREND_TIMEFRAME = "1h"

# Risk parameters
MAX_POSITIONS = 3
DEFAULT_RISK_PER_TRADE = 0.02  # 2% of account

# ML settings
TRAINING_DAYS = 30
RETRAIN_INTERVAL_HOURS = 24
MODEL_PATH = "/app/data/model.pkl"

# Gemini API key (get from https://makersuite.google.com/app/apikey)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
