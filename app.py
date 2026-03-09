import streamlit as st
import pandas as pd
from scanner import CryptoScanner
from datetime import datetime
import time

st.set_page_config(page_title="Crypto Signal Scanner", layout="wide")
st.title("📡 Self‑Learning Crypto Scanner")

# Initialize scanner in session state
if 'scanner' not in st.session_state:
    st.session_state.scanner = CryptoScanner()
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['timestamp', 'pair', 'signal', 'price'])

# Pairs to scan
pairs = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT"]

# Sidebar
with st.sidebar:
    st.header("Settings")
    scan_interval = st.slider("Scan interval (seconds)", 30, 300, 60)
    auto_refresh = st.checkbox("Auto refresh", value=True)

# Main area
col1, col2 = st.columns(2)

with col1:
    st.subheader("Current Signals")
    if st.button("Scan Now"):
        with st.spinner("Scanning..."):
            signals = st.session_state.scanner.scan_pairs(pairs)
            if signals:
                for pair, (signal, price) in signals.items():
                    st.success(f"{pair}: {signal} at ${price:.2f}")
                    # Append to history
                    new_row = pd.DataFrame([{
                        'timestamp': datetime.now(),
                        'pair': pair,
                        'signal': signal,
                        'price': price
                    }])
                    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
            else:
                st.info("No signals at the moment.")

with col2:
    st.subheader("Signal History")
    if not st.session_state.history.empty:
        st.dataframe(st.session_state.history.tail(20), use_container_width=True)
    else:
        st.write("No signals yet. Click 'Scan Now' to start.")

# Auto refresh
if auto_refresh:
    time.sleep(scan_interval)
    st.rerun()
