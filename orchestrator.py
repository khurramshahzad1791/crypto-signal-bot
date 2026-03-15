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
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from agents.market_analyst import MarketAnalyst
from agents.news_sentiment import NewsSentimentAgent
from agents.technical_strategist import TechnicalStrategist
from agents.risk_manager import RiskManager
from agents.execution_optimizer import ExecutionOptimizer
from chat import TradingChat
from trade_logger import Session, Trade, SignalLog

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
        self.signals = []  # in-memory for UI
        self.running = True
        self.last_scan_time = None
        self.scan_count = 0
        self.status_message = "Initializing..."
        self.last_error = None
        self.lock = threading.Lock()

    async def run_cycle(self):
        try:
            self.status_message = "Scanning markets..."
            self.last_error = None
            market_signals = await self.agents['market_analyst'].analyze()
            logger.info(f"Market analyst returned: {market_signals}")

            if market_signals:
                db_session = Session()
                with self.lock:
                    for signal in market_signals:
                        if 'timestamp' not in signal:
                            signal['timestamp'] = datetime.now()
                        self.signals.append(signal)
                        # Log to database
                        signal_log = SignalLog(
                            pair=signal['pair'],
                            signal_type=f"{signal['direction']}_{signal.get('strategy','unknown')}",
                            price=signal['price'],
                            confidence=signal['confidence']
                        )
                        db_session.add(signal_log)
                        logger.info(f"Signal logged to DB: {signal['pair']}")
                    db_session.commit()
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

background_thread_started = False

def start_background_loop(orchestrator_ref):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(orchestrator_ref.run_forever())
    except Exception as e:
        logger.error(f"Background thread crashed: {e}", exc_info=True)

def main():
    global background_thread_started

    st.set_page_config(page_title="AI Trading System", layout="wide")
    st.title("🤖 Multi‑Agent AI Trading System")

    if 'orchestrator' not in st.session_state:
        st.session_state.orchestrator = TradingOrchestrator()
        if not background_thread_started:
            thread = threading.Thread(
                target=start_background_loop,
                args=(st.session_state.orchestrator,),
                daemon=True
            )
            thread.start()
            background_thread_started = True
            logger.info("Background thread started.")

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

    tab1, tab2, tab3, tab4 = st.tabs(["📡 Signals", "📊 Performance", "💬 Chat", "🧠 Learner"])

    with tab1:
        st.subheader("Live Signals")
        if orch.signals:
            df = pd.DataFrame(orch.signals[-50:][::-1])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No signals yet. Waiting for market analysis...")

    with tab2:
        st.subheader("Performance Analytics")
        # Load trades from database
        db_session = Session()
        trades = db_session.query(Trade).order_by(Trade.timestamp.desc()).limit(100).all()
        if trades:
            df_trades = pd.DataFrame([{
                'time': t.timestamp,
                'pair': t.pair,
                'signal': t.signal_type,
                'entry': t.entry_price,
                'exit': t.exit_price,
                'pnl%': t.pnl_percent,
                'outcome': t.outcome
            } for t in trades])
            st.dataframe(df_trades, use_container_width=True)

            # Stats
            wins = df_trades[df_trades['outcome'] == 'win']
            losses = df_trades[df_trades['outcome'] == 'loss']
            win_rate = len(wins) / (len(wins) + len(losses)) * 100 if len(wins)+len(losses) > 0 else 0
            total_pnl = df_trades['pnl%'].sum() if 'pnl%' in df_trades else 0
            col1, col2, col3 = st.columns(3)
            col1.metric("Win Rate", f"{win_rate:.1f}%")
            col2.metric("Total P&L %", f"{total_pnl:.2f}%")
            col3.metric("Total Trades", len(df_trades))

            # Equity curve
            if 'pnl%' in df_trades and not df_trades.empty:
                df_trades['cumulative'] = df_trades['pnl%'].cumsum()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_trades['time'], y=df_trades['cumulative'],
                                          mode='lines', name='Equity Curve'))
                fig.update_layout(title='Equity Curve (Cumulative P&L %)')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trades yet. Take signals to start building history.")

    with tab3:
        st.subheader("AI Chat Assistant")
        if 'chat' not in st.session_state:
            st.session_state.chat = TradingChat()

        user_input = st.text_input("You:", key="chat_input")
        if st.button("Send"):
            if user_input:
                recent_signals = orch.signals[-5:] if orch.signals else []
                db_session = Session()
                recent_trades = db_session.query(Trade).order_by(Trade.timestamp.desc()).limit(5).all()
                response = st.session_state.chat.get_response(user_input, recent_signals, recent_trades)
                st.text_area("Assistant:", response, height=200)

    with tab4:
        st.subheader("Machine Learning Training")
        st.write("This tab will train a model on historical signal outcomes to improve future predictions.")
        if st.button("Train Model Now"):
            from learner import StrategyLearner
            learner = StrategyLearner()
            with st.spinner("Training... (may take a few minutes)"):
                learner.train()
            st.success("Training complete!")

if __name__ == "__main__":
    main()
