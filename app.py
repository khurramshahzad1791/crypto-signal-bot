import streamlit as st
import pandas as pd
from datetime import datetime
import time
from scanner import CryptoScanner
from chat import TradingChat
from trade_logger import Session, Trade, SignalLog
import config

st.set_page_config(page_title="AI Crypto Trader", layout="wide")
st.title("🤖 AI Crypto Trading Assistant")

# Initialize components
if 'scanner' not in st.session_state:
    st.session_state.scanner = CryptoScanner()
if 'chat' not in st.session_state:
    st.session_state.chat = TradingChat()
if 'signals' not in st.session_state:
    st.session_state.signals = []
if 'last_scan' not in st.session_state:
    st.session_state.last_scan = None

# Sidebar
with st.sidebar:
    st.header("Controls")
    scan_interval = st.slider("Scan interval (seconds)", 60, 600, 120)
    auto_refresh = st.checkbox("Auto refresh", value=True)

    st.header("Risk Settings")
    account_balance = st.number_input("Account (USDT)", value=1000, step=100)
    risk_per_trade = st.slider("Risk per trade (%)", 0.5, 5.0, 2.0) / 100

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📡 Signals", "📊 Performance", "💬 Chat", "⚙️ Learner"])

# -------------------- Tab 1: Signals --------------------
with tab1:
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Scan Now"):
            with st.spinner("Scanning markets..."):
                st.session_state.signals = st.session_state.scanner.scan_pairs()
                st.session_state.last_scan = datetime.now()

    with col2:
        if st.session_state.last_scan:
            st.info(f"Last scan: {st.session_state.last_scan.strftime('%H:%M:%S')}")

    if st.session_state.signals:
        df_signals = pd.DataFrame(st.session_state.signals)
        st.dataframe(df_signals, width='stretch')

        if st.checkbox("Show take trade buttons (simulated)"):
            for idx, row in df_signals.iterrows():
                if st.button(f"Take {row['pair']} {row['direction']}", key=f"take_{idx}"):
                    session = Session()
                    trade = Trade(
                        pair=row['pair'],
                        signal_type=f"{row['direction']}_{row['strategy']}",
                        entry_price=row['price'],
                        stop_loss=row['stop_loss'],
                        take_profit=row['take_profit'],
                        confidence=row['confidence'],
                        outcome='open'
                    )
                    session.add(trade)
                    session.commit()
                    st.success(f"Trade taken: {row['pair']} at {row['price']}")
    else:
        st.info("No signals yet. Click 'Scan Now'.")

# -------------------- Tab 2: Performance --------------------
with tab2:
    st.subheader("Trade History")
    session = Session()
    trades = session.query(Trade).order_by(Trade.timestamp.desc()).limit(100).all()
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
        st.dataframe(df_trades, width='stretch')

        wins = df_trades[df_trades['outcome'] == 'win']
        losses = df_trades[df_trades['outcome'] == 'loss']
        win_rate = len(wins) / (len(wins) + len(losses)) * 100 if len(wins)+len(losses) > 0 else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    else:
        st.info("No trades yet.")

# -------------------- Tab 3: Chat --------------------
with tab3:
    st.subheader("Ask your AI assistant")
    user_input = st.text_input("You:", key="chat_input")
    if st.button("Send"):
        if user_input:
            recent_signals = st.session_state.signals[-3:] if st.session_state.signals else []
            recent_trades = trades[:5] if trades else []
            response = st.session_state.chat.get_response(user_input, recent_signals, recent_trades)
            st.text_area("Assistant:", response, height=200)

# -------------------- Tab 4: Learner --------------------
with tab4:
    st.subheader("Machine Learning Training")
    if st.button("Train Model Now"):
        from learner import StrategyLearner
        learner = StrategyLearner()
        with st.spinner("Training... (may take a few minutes)"):
            learner.train()
        st.success("Training complete!")

# Auto refresh
if auto_refresh:
    time.sleep(scan_interval)
    st.rerun()
