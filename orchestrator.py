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
from learner import StrategyLearner

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
        self.learner = StrategyLearner()
        self.signals = []
        self.running = True
        self.last_scan_time = None
        self.scan_count = 0
        self.status_message = "Initializing..."
        self.last_error = None
        self.lock = threading.Lock()
        self.last_training = None

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
                        # Add ML probability
                        ml_prob = self.learner.predict_win_probability(signal)
                        signal['ml_prob'] = round(ml_prob, 2)
                        # Optionally adjust confidence
                        signal['confidence'] = int((signal['confidence'] + ml_prob * 100) / 2)

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

            # Auto-retrain once per day
            if self.last_training is None or (datetime.now() - self.last_training).total_seconds() > 86400:
                threading.Thread(target=self.learner.train).start()
                self.last_training = datetime.now()

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

    # Sidebar settings
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

        st.sidebar.header("Trading Settings")
        account_balance = st.sidebar.number_input("Account Balance (USDT)", value=1000, step=100)
        risk_percent = st.sidebar.slider("Risk per trade (%)", 0.5, 5.0, 2.0) / 100
        leverage = st.sidebar.selectbox("Leverage", [1, 5, 10, 20, 50, 100], index=5)
        st.sidebar.subheader("Strategies")
        use_mean_reversion = st.sidebar.checkbox("Mean Reversion", True)
        use_breakout = st.sidebar.checkbox("Breakout", True)
        use_trend = st.sidebar.checkbox("Trend Continuation", True)

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📡 Signals", "📊 Performance", "💬 Chat", "🧠 Learner", "📈 Chart", "🤖 Agent Chat"
    ])

    with tab1:
        st.subheader("Live Signals")
        if orch.signals:
            # Filter signals based on strategy toggles
            filtered = []
            for s in orch.signals[-50:]:
                strat = s.get('strategy', '')
                if (strat == 'mean_reversion' and not use_mean_reversion) or \
                   (strat == 'breakout' and not use_breakout) or \
                   (strat == 'trend_continuation' and not use_trend):
                    continue
                filtered.append(s)
            if filtered:
                df = pd.DataFrame(filtered[::-1])
                # Add position size column
                def compute_size(row):
                    stop_dist = abs(row['price'] - row['stop_loss'])
                    if stop_dist == 0:
                        return 0
                    risk_amount = account_balance * risk_percent
                    pos_size = risk_amount / stop_dist
                    return round(pos_size, 2)
                df['position_size'] = df.apply(compute_size, axis=1)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No signals match your selected strategies.")
        else:
            st.info("No signals yet. Waiting for market analysis...")

    with tab2:
        st.subheader("Performance Analytics")
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

            wins = df_trades[df_trades['outcome'] == 'win']
            losses = df_trades[df_trades['outcome'] == 'loss']
            win_rate = len(wins) / (len(wins) + len(losses)) * 100 if len(wins)+len(losses) > 0 else 0
            total_pnl = df_trades['pnl%'].sum() if 'pnl%' in df_trades else 0
            col1, col2, col3 = st.columns(3)
            col1.metric("Win Rate", f"{win_rate:.1f}%")
            col2.metric("Total P&L %", f"{total_pnl:.2f}%")
            col3.metric("Total Trades", len(df_trades))

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
        st.write("This tab trains a model on historical signal outcomes to improve future predictions.")
        if st.button("Train Model Now"):
            with st.spinner("Training... (may take a few minutes)"):
                orch.learner.train()
            st.success("Training complete!")

    with tab5:
        st.subheader("Interactive Chart Analysis")
        col1, col2 = st.columns([1, 3])
        with col1:
            chart_pair = st.selectbox("Select Pair", orch.agents['market_analyst'].pairs)
            chart_days = st.slider("Days of history", 1, 30, 7)
            show_support = st.checkbox("Show Support/Resistance", True)
            show_trendlines = st.checkbox("Show Trendlines", True)
            if st.button("🔄 Refresh Chart"):
                st.rerun()
        with col2:
            ma = orch.agents['market_analyst']
            df = ma.fetch_ohlcv(chart_pair, '1h', 24*chart_days)
            if df is not None:
                highs = df['high'].values
                lows = df['low'].values
                support_levels = []
                resistance_levels = []
                for i in range(2, len(df)-2):
                    if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                        support_levels.append((df['timestamp'].iloc[i], lows[i]))
                    if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                        resistance_levels.append((df['timestamp'].iloc[i], highs[i]))

                fig = go.Figure(data=[go.Candlestick(
                    x=df['timestamp'],
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name='Price'
                )])
                if show_support:
                    for ts, level in support_levels[-10:]:
                        fig.add_hline(y=level, line_dash="dot", line_color="green", opacity=0.3)
                if show_trendlines:
                    if len(support_levels) >= 2:
                        x_vals = [support_levels[-2][0], support_levels[-1][0]]
                        y_vals = [support_levels[-2][1], support_levels[-1][1]]
                        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name='Uptrend', line=dict(color='lime', dash='dash')))
                    if len(resistance_levels) >= 2:
                        x_vals = [resistance_levels[-2][0], resistance_levels[-1][0]]
                        y_vals = [resistance_levels[-2][1], resistance_levels[-1][1]]
                        fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', name='Downtrend', line=dict(color='red', dash='dash')))

                df['ema20'] = df['close'].ewm(span=20).mean()
                df['ema50'] = df['close'].ewm(span=50).mean()
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema20'], name='EMA20', line=dict(color='orange')))
                fig.add_trace(go.Scatter(x=df['timestamp'], y=df['ema50'], name='EMA50', line=dict(color='blue')))

                fig.update_layout(title=f"{chart_pair} – Last {chart_days} days", height=500)
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Ask about this chart")
                chart_query = st.text_input("Your question about the chart:")
                if st.button("Ask Gemini about chart"):
                    if chart_query and 'chat' in st.session_state:
                        context = f"Current price: {df['close'].iloc[-1]:.2f}. "
                        if support_levels:
                            context += f"Recent support near {support_levels[-1][1]:.2f}. "
                        if resistance_levels:
                            context += f"Recent resistance near {resistance_levels[-1][1]:.2f}. "
                        prompt = f"Regarding the {chart_pair} chart, {context} User asks: {chart_query}"
                        response = st.session_state.chat.get_response(prompt, [], [])
                        st.text_area("Gemini:", response, height=150)
            else:
                st.error("Failed to fetch data.")

    with tab6:
        st.subheader("Agent Team Chat")
        st.write("Chat with all your agents collectively. They will collaborate to answer your questions.")
        user_query = st.text_input("Ask the agent team:", key="agent_chat_input")
        if st.button("Ask Agents"):
            if user_query:
                # Gather context from all agents
                market_ctx = "Market Analyst: " + (str(orch.signals[-3:]) if orch.signals else "No recent signals")
                news_ctx = "News Sentiment: " + (str(orch.agents['news_sentiment'].analyze()) if hasattr(orch.agents['news_sentiment'], 'analyze') else "Neutral")
                # Simulate a combined response using Gemini
                prompt = f"""You are a team of trading agents: market analyst, news analyst, technical strategist, risk manager, and execution optimizer.
A user asks: {user_query}
Provide a collaborative answer incorporating insights from each agent. Be concise and helpful.
Current context: {market_ctx} | {news_ctx}
"""
                if 'chat' in st.session_state:
                    response = st.session_state.chat.get_response(prompt, [], [])
                    st.text_area("Agent Team:", response, height=300)
                else:
                    st.error("Chat not initialized.")

if __name__ == "__main__":
    main()
