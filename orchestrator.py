import streamlit as st
import asyncio
import logging
from fastapi import FastAPI
import uvicorn
import threading
import time
from datetime import datetime
import pandas as pd
import traceback

from agents.market_analyst import MarketAnalyst
from agents.news_sentiment import NewsSentimentAgent
from agents.technical_strategist import TechnicalStrategist
from agents.risk_manager import RiskManager
from agents.execution_optimizer import ExecutionOptimizer
from chat import TradingChat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Agent Trading System")

@app.get("/")
async def root():
    return {"status": "online", "service": "Trading System"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

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
        self.last_scan_time = None
        self.scan_count = 0
        self.status_message = "Initializing..."
        self.last_error = None
        self.lock = threading.Lock()  # for thread-safe access

    async def run_cycle(self):
        try:
            self.status_message = "Scanning markets..."
            self.last_error = None
            market_signals = await self.agents['market_analyst'].analyze()
            logger.info(f"Market analyst returned: {market_signals}")

            if market_signals:
                with self.lock:
                    for signal in market_signals:
                        if 'timestamp' not in signal:
                            signal['timestamp'] = datetime.now()
                        self.signals.append(signal)
                        logger.info(f"Signal generated: {signal}")
                    self.scan_count += len(market_signals)
                self.status_message = f"Last scan: {datetime.now().strftime('%H:%M:%S')} – {len(market_signals)} signals found."
            else:
                self.status_message = f"Last scan: {datetime.now().strftime('%H:%M:%S')} – No signals."

            self.last_scan_time = datetime.now()
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Cycle error: {e}\n{error_trace}")
            self.last_error = str(e)
            self.status_message = f"Error in scan: {str(e)}"

    async def run_forever(self):
        while self.running:
            await self.run_cycle()
            await asyncio.sleep(300)

# Global orchestrator instance (will be stored in session state)
orchestrator = None
background_thread_started = False

def start_background_loop(orchestrator_ref):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(orchestrator_ref.run_forever())

def main():
    global orchestrator, background_thread_started

    st.set_page_config(page_title="AI Trading System", layout="wide")
    st.title("🤖 Multi‑Agent AI Trading System")

    # Initialize orchestrator in session state
    if 'orchestrator' not in st.session_state:
        st.session_state.orchestrator = TradingOrchestrator()
        # Start background thread only once
        if not background_thread_started:
            thread = threading.Thread(target=start_background_loop, args=(st.session_state.orchestrator,), daemon=True)
            thread.start()
            background_thread_started = True

    orch = st.session_state.orchestrator

    with st.sidebar:
        st.header("System Status")
        st.write(f"Agents active: {len(orch.agents)}")
        st.write(f"Total signals generated: {len(orch.signals)}")
        st.write(f"Last scan: {orch.last_scan_time.strftime('%H:%M:%S') if orch.last_scan_time else 'Never'}")
        st.write(f"Status: {orch.status_message}")
        if orch.last_error:
            st.error(f"Last error: {orch.last_error}")

        if st.button("🔄 Scan Now"):
            with st.spinner("Scanning..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(orch.run_cycle())
                st.success("Scan complete!")
                st.rerun()

    tab1, tab2, tab3 = st.tabs(["📡 Signals", "📊 Performance", "💬 Chat"])

    with tab1:
        st.subheader("Live Signals")
        if orch.signals:
            # Show most recent signals first
            df = pd.DataFrame(orch.signals[-20:][::-1])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No signals yet. Waiting for market analysis...")

    with tab2:
        st.subheader("Performance (coming soon)")
        st.write("Trade history and win rate will appear here.")

    with tab3:
        st.subheader("AI Chat Assistant")
        if 'chat' not in st.session_state:
            st.session_state.chat = TradingChat()

        user_input = st.text_input("You:", key="chat_input")
        if st.button("Send"):
            if user_input:
                recent_signals = orch.signals[-5:] if orch.signals else []
                response = st.session_state.chat.get_response(user_input, recent_signals, [])
                st.text_area("Assistant:", response, height=200)

if __name__ == "__main__":
    main()
