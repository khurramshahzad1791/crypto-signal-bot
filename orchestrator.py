import streamlit as st
import asyncio
import logging
from fastapi import FastAPI
import uvicorn
import threading
import time
from datetime import datetime
import pandas as pd

# Import agents
from agents.market_analyst import MarketAnalyst
from agents.news_sentiment import NewsSentimentAgent
from agents.technical_strategist import TechnicalStrategist
from agents.risk_manager import RiskManager
from agents.execution_optimizer import ExecutionOptimizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- FastAPI app (for health checks and API) ----------
app = FastAPI(title="Multi-Agent Trading System")

@app.get("/")
async def root():
    return {"status": "online", "service": "Trading System"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# ---------- Trading Orchestrator ----------
class TradingOrchestrator:
    def __init__(self):
        self.agents = {
            'market_analyst': MarketAnalyst(),
            'news_sentiment': NewsSentimentAgent(),
            'technical_strategist': TechnicalStrategist(),
            'risk_manager': RiskManager(),
            'execution_optimizer': ExecutionOptimizer()
        }
        self.signals = []
        self.running = True

    async def run_cycle(self):
        """One analysis cycle"""
        try:
            # Market analyst signal
            ma_signal = await self.agents['market_analyst'].analyze()
            # Technical strategist signal
            ts_signal = await self.agents['technical_strategist'].analyze()
            # News sentiment
            news = await self.agents['news_sentiment'].analyze()

            # Combine signals
            if ma_signal and ts_signal and ma_signal['pair'] == ts_signal['pair']:
                if ma_signal['direction'] == ts_signal['direction']:
                    confidence = (ma_signal['confidence'] + ts_signal['confidence']) / 2
                    # Risk check
                    risk_ok = await self.agents['risk_manager'].check(ma_signal, confidence)
                    if risk_ok and confidence >= 70:
                        signal = {
                            'timestamp': datetime.now(),
                            'pair': ma_signal['pair'],
                            'direction': ma_signal['direction'],
                            'entry': ma_signal['price'],
                            'stop_loss': ma_signal['stop_loss'],
                            'take_profit': ma_signal['take_profit'],
                            'confidence': confidence,
                            'news_sentiment': news['sentiment']
                        }
                        self.signals.append(signal)
                        logger.info(f"Signal generated: {signal}")
        except Exception as e:
            logger.error(f"Cycle error: {e}")

    async def run_forever(self):
        while self.running:
            await self.run_cycle()
            await asyncio.sleep(300)  # 5 minutes

orchestrator = TradingOrchestrator()

# ---------- Background thread for async loop ----------
def start_background_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(orchestrator.run_forever())

threading.Thread(target=start_background_loop, daemon=True).start()

# ---------- Streamlit UI ----------
def main():
    st.set_page_config(page_title="AI Trading System", layout="wide")
    st.title("🤖 Multi‑Agent AI Trading System")

    # Sidebar
    with st.sidebar:
        st.header("Status")
        st.write(f"Agents active: {len(orchestrator.agents)}")
        st.write(f"Signals generated: {len(orchestrator.signals)}")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📡 Signals", "📊 Performance", "💬 Chat"])

    with tab1:
        st.subheader("Live Signals")
        if orchestrator.signals:
            df = pd.DataFrame(orchestrator.signals[-20:])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No signals yet. Waiting for market analysis...")

    with tab2:
        st.subheader("Performance (coming soon)")
        st.write("Trade history and win rate will appear here.")

    with tab3:
        st.subheader("AI Chat Assistant")
        st.write("Chat with your trading assistant (requires API key).")
        user_input = st.text_input("You:")
        if user_input:
            # Placeholder for LLM response
            st.text_area("Assistant:", "AI response placeholder – configure API key to enable.")

if __name__ == "__main__":
    # If script is run directly, start Streamlit
    main()
