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

class PaperTrade:
    """Represents an open paper trade"""
    def __init__(self, signal, db_session):
        self.signal = signal
        self.entry_time = signal['timestamp']
        self.entry_price = signal['price']
        self.direction = signal['direction']
        self.stop_loss = signal['stop_loss']
        self.take_profit = signal['take_profit']
        self.pair = signal['pair']
        self.confidence = signal['confidence']
        self.strategy = signal.get('strategy', 'unknown')
        self.status = 'open'
        self.db_session = db_session
        trade = Trade(
            pair=self.pair,
            signal_type=f"{self.direction}_{self.strategy}",
            entry_price=self.entry_price,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            confidence=self.confidence,
            outcome='open'
        )
        db_session.add(trade)
        db_session.commit()
        self.db_id = trade.id

    def check_exit(self, current_price):
        if self.direction == 'LONG':
            if current_price >= self.take_profit:
                return 'win', self.take_profit
            elif current_price <= self.stop_loss:
                return 'loss', self.stop_loss
        else:
            if current_price <= self.take_profit:
                return 'win', self.take_profit
            elif current_price >= self.stop_loss:
                return 'loss', self.stop_loss
        return None, None

    def close(self, outcome, exit_price):
        pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        if self.direction == 'SHORT':
            pnl_pct = -pnl_pct
        trade = self.db_session.query(Trade).filter_by(id=self.db_id).first()
        trade.exit_price = exit_price
        trade.outcome = outcome
        trade.pnl_percent = round(pnl_pct, 2)
        self.db_session.commit()
        self.status = outcome
        logger.info(f"Closed {self.pair} {self.direction} at {exit_price} for {outcome} ({pnl_pct:.2f}%)")

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
        self.open_positions = []
        self.running = True
        self.last_scan_time = None
        self.scan_count = 0
        self.status_message = "Initializing..."
        self.last_error = None
        self.lock = threading.Lock()
        self.last_training = None
        self.db_session = Session()

    async def run_cycle(self):
        try:
            self.status_message = "Scanning markets..."
            self.last_error = None
            market_signals = await self.agents['market_analyst'].analyze()
            logger.info(f"Market analyst returned {len(market_signals) if market_signals else 0} signals")

            # Check open positions for exits
            still_open = []
            for pos in self.open_positions:
                df = self.agents['market_analyst'].fetch_ohlcv(pos.pair, '1m', 1)
                if df is not None:
                    current_price = df['close'].iloc[-1]
                    outcome, exit_price = pos.check_exit(current_price)
                    if outcome:
                        pos.close(outcome, exit_price)
                    else:
                        still_open.append(pos)
                else:
                    still_open.append(pos)
            self.open_positions = still_open

            # Open new trades from signals
            if market_signals:
                with self.lock:
                    for signal in market_signals:
                        if any(pos.pair == signal['pair'] for pos in self.open_positions):
                            continue
                        if signal['confidence'] < 70:
                            continue
                        ml_prob = self.learner.predict_win_probability(signal)
                        signal['ml_prob'] = round(ml_prob, 2)
                        signal['confidence'] = int((signal['confidence'] + ml_prob * 100) / 2)
                        trade = PaperTrade(signal, self.db_session)
                        self.open_positions.append(trade)
                        logger.info(f"Opened paper trade: {signal['pair']} {signal['direction']} at {signal['price']}")
                    self.signals.extend(market_signals)
                    self.scan_count += len(market_signals)
                self.status_message = f"Last scan: {datetime.now().strftime('%H:%M:%S')} – {len(market_signals)} signals, {len(self.open_positions)} open positions."
            else:
                self.status_message = f"Last scan: {datetime.now().strftime('%H:%M:%S')} – No signals, {len(self.open_positions)} open positions."

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
    st.title("🤖 Autonomous AI Trading System")

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
        st.write(f"Open positions: {len(orch.open_positions)}")
        st.write(f"Last scan: {orch.last_scan_time.strftime('%H:%M:%S') if orch.last_scan_time else 'Never'}")
        st.write(f"Status: {orch.status_message}")
        if orch.last_error:
            st.error(f"Last error: {orch.last_error}")

        st.sidebar.header("Account Settings")
        account_balance = st.sidebar.number_input("Account Balance (USDT)", value=1000, step=100)
        risk_percent = st.sidebar.slider("Risk per trade (%)", 0.5, 5.0, 2.0) / 100
        leverage = st.sidebar.selectbox("Leverage (for info)", [1, 5, 10, 20, 50, 100], index=5)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📡 Live Signals", "📊 Open Positions", "📈 Performance", "💬 Chat", "📉 Chart", "🤖 Agent Chat"
    ])

    with tab1:
        st.subheader("Latest Signals")
        if orch.signals:
            df = pd.DataFrame(orch.signals[-50:][::-1])
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
            st.info("No signals yet. Waiting for market analysis...")

    with tab2:
        st.subheader("Open Paper Trades")
        if orch.open_positions:
            data = []
            for pos in orch.open_positions:
                df = orch.agents['market_analyst'].fetch_ohlcv(pos.pair, '1m', 1)
                current = df['close'].iloc[-1] if df is not None else 'N/A'
                data.append({
                    'Pair': pos.pair,
                    'Direction': pos.direction,
                    'Entry': pos.entry_price,
                    'Current': current,
                    'SL': pos.stop_loss,
                    'TP': pos.take_profit,
                    'P&L %': f"{((current - pos.entry_price)/pos.entry_price*100):.2f}" if current != 'N/A' else 'N/A'
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No open positions.")

    with tab3:
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
            st.info("No trades yet. The system will start paper trading automatically.")

    with tab4:
        st.subheader("AI Chat Assistant")
        if 'chat' not in st.session_state:
            st.session_state.chat = TradingChat()
            st.session_state.messages = []

        # Display chat messages from history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # React to user input
        if prompt := st.chat_input("You:"):
            # Display user message
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            # Get assistant response
            recent_signals = orch.signals[-5:] if orch.signals else []
            db_session = Session()
            recent_trades = db_session.query(Trade).order_by(Trade.timestamp.desc()).limit(5).all()
            response = st.session_state.chat.get_response(prompt, recent_signals, recent_trades)

            # Display assistant response
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

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
        if 'agent_chat_history' not in st.session_state:
            st.session_state.agent_chat_history = []

        for msg in st.session_state.agent_chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        agent_query = st.chat_input("Ask the agent team:")
        if agent_query:
            st.chat_message("user").markdown(agent_query)
            st.session_state.agent_chat_history.append({"role": "user", "content": agent_query})

            # Get news sentiment asynchronously (but we're in a sync context, so we'll handle)
            news_ctx = "Neutral"
            try:
                # We need to run async in sync context – quick hack: create new loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                news_result = loop.run_until_complete(orch.agents['news_sentiment'].analyze())
                news_ctx = news_result.get('summary', 'Neutral')
            except:
                pass

            market_ctx = "Market Analyst: " + (str(orch.signals[-3:]) if orch.signals else "No recent signals")
            prompt = f"""You are a team of trading agents: market analyst, news analyst, technical strategist, risk manager, and execution optimizer.
A user asks: {agent_query}
Provide a collaborative answer incorporating insights from each agent. Be concise and helpful.
Current context: {market_ctx} | News Sentiment: {news_ctx}
"""
            if 'chat' in st.session_state:
                response = st.session_state.chat.get_response(prompt, [], [])
                with st.chat_message("assistant"):
                    st.markdown(response)
                st.session_state.agent_chat_history.append({"role": "assistant", "content": response})
            else:
                st.error("Chat not initialized.")

if __name__ == "__main__":
    main()
