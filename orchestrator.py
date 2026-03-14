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
from chat import TradingChat  # <-- added chat import

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
        self.last_scan_time = None
        self.scan_count = 0
        self.status_message = "Initializing..."

    async def run_cycle(self):
        """One analysis cycle – updates signals and status"""
        try:
            self.status_message = "Scanning markets..."
            # Market analyst now returns a list of signals (multiple pairs/strategies)
            market_signals = await self.agents['market_analyst'].analyze()
            
            # Technical strategist (placeholder – can be expanded later)
            ts_signal = await self.agents['technical_strategist'].analyze()
            # News sentiment
            news = await self.agents['news_sentiment'].analyze()

            # Process market signals
            if market_signals:
                for signal in market_signals:
                    # Add timestamp if missing
                    if 'timestamp' not in signal:
                        signal['timestamp'] = datetime.now()
                    # Optionally add news sentiment to signal
                    signal['news_sentiment'] = news['sentiment']
                    self.signals.append(signal)
                    logger.info(f"Signal generated: {signal}")
                self.scan_count += len(market_signals)
            
            self.last_scan_time = datetime.now()
            self.status_message = f"Last scan: {self.last_scan_time.strftime('%H:%M:%S')} – {len(market_signals) if market_signals else 0} signals found."
            
        except Exception as e:
            logger.error(f"Cycle error: {e}")
            self.status_message = f"Error in scan: {str(e)}"

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

    # Sidebar with status and manual scan button
    with st.sidebar:
        st.header("System Status")
        st.write(f"Agents active: {len(orchestrator.agents)}")
        st.write(f"Total signals generated: {len(orchestrator.signals)}")
        st.write(f"Last scan: {orchestrator.last_scan_time.strftime('%H:%M:%S') if orchestrator.last_scan_time else 'Never'}")
        st.write(f"Status: {orchestrator.status_message}")
        
        # Manual scan button
        if st.button("🔄 Scan Now"):
            with st.spinner("Scanning..."):
                # Run a cycle synchronously (blocks UI briefly)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(orchestrator.run_cycle())
                st.success("Scan complete!")
                st.rerun()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📡 Signals", "📊 Performance", "💬 Chat"])

    with tab1:
        st.subheader("Live Signals")
        if orchestrator.signals:
            # Show most recent signals first (reverse order)
            df = pd.DataFrame(orchestrator.signals[-20:][::-1])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No signals yet. Waiting for market analysis...")

    with tab2:
        st.subheader("Performance (coming soon)")
        st.write("Trade history and win rate will appear here.")

    with tab3:
        st.subheader("AI Chat Assistant")
        # Initialize chat if not in session state
        if 'chat' not in st.session_state:
            st.session_state.chat = TradingChat()
        
        user_input = st.text_input("You:", key="chat_input")
        if st.button("Send"):
            if user_input:
                # Get recent signals for context
                recent_signals = orchestrator.signals[-5:] if orchestrator.signals else []
                # Trade history not implemented yet
                response = st.session_state.chat.get_response(user_input, recent_signals, [])
                st.text_area("Assistant:", response, height=200)

if __name__ == "__main__":
    main()
