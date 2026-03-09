import ccxt
import pandas as pd
import numpy as np
from datetime import datetime

class CryptoScanner:
    def __init__(self):
        self.exchange = ccxt.mexc({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

    def fetch_data(self, symbol, timeframe='5m', limit=200):
        """Fetch OHLCV data"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None

    def calculate_indicators(self, df):
        """Add RSI and MACD"""
        close = df['close']

        # RSI (14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD (12,26,9)
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        return df

    def generate_signals(self, df):
        """Return buy/sell signals based on RSI and MACD"""
        last = df.iloc[-1]
        prev = df.iloc[-2]

        signals = []
        # Long signal: RSI < 30 and MACD histogram rising from below zero
        if last['rsi'] < 30 and last['macd_hist'] > prev['macd_hist'] and last['macd_hist'] < 0:
            signals.append(('LONG', last['close']))

        # Short signal: RSI > 70 and MACD histogram falling from above zero
        if last['rsi'] > 70 and last['macd_hist'] < prev['macd_hist'] and last['macd_hist'] > 0:
            signals.append(('SHORT', last['close']))

        return signals

    def scan_pairs(self, pair_list):
        results = {}
        for pair in pair_list:
            df = self.fetch_data(pair)
            if df is not None:
                df = self.calculate_indicators(df)
                signals = self.generate_signals(df)
                if signals:
                    # Take the latest signal
                    results[pair] = signals[-1]
        return results
