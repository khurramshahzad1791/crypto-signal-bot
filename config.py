import os
from dotenv import load_dotenv

load_dotenv()

# Trading Configuration
TRADING_PAIRS = [
    "BTC/USDT",
    "ETH/USDT", 
    "XRP/USDT",
    "SOL/USDT"
]

TIMEFRAMES = {
    "entry": "5m",
    "trend": "1h",
    "analysis": "4h"
}

# Risk Management
MAX_POSITIONS = 3
MAX_LEVERAGE = 100
RISK_PER_TRADE = 0.02  # 2% of account
MIN_CONFIDENCE_SCORE = 70

# API Keys (set in Railway Variables)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")
JINA_API_KEY = os.getenv("JINA_API_KEY")

# Multi-Agent Configuration
AGENTS = {
    "market_analyst": True,
    "news_sentiment": True,
    "technical_strategist": True,
    "risk_manager": True,
    "execution_optimizer": True
}

# Model Storage
MODEL_PATH = "/app/models/"
DATA_PATH = "/app/data/"
LOG_PATH = "/app/logs/"
