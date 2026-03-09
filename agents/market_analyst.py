import ccxt
import pandas as pd
import numpy as np
from datetime import datetime

class MarketAnalyst:
    def __init__(self):
        self.exchange = ccxt.mexc({'enableRateLimit': True})

    async def analyze(self):
        try:
            # For simplicity, analyze only BTC/USDT
            df = self.fetch_ohlcv('BTC/USDT', '5m', 200)
            if df is None:
                return None
            df = self.add_indicators(df)
            signal = self.generate_signal(df)
            return signal
        except Exception as e:
            print(f"MarketAnalyst error: {e}")
            return None

    def fetch_ohlcv(self, symbol, timeframe, limit):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except:
            return None

    def add_indicators(self, df):
        close = df['close']
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        df['ema9'] = close.ewm(span=9).mean()
        df['ema21'] = close.ewm(span=21).mean()
        df['ema200'] = close.ewm(span=200).mean()
        return df

    def generate_signal(self, df):
        last = df.iloc[-1]
        # Simple RSI strategy
        if last['rsi'] < 30:
            return {
                'pair': 'BTC/USDT',
                'direction': 'LONG',
                'price': last['close'],
                'confidence': 80,
                'stop_loss': last['close'] * 0.98,
                'take_profit': last['close'] * 1.05,
                'reason': 'RSI oversold'
            }
        if last['rsi'] > 70:
            return {
                'pair': 'BTC/USDT',
                'direction': 'SHORT',
                'price': last['close'],
                'confidence': 80,
                'stop_loss': last['close'] * 1.02,
                'take_profit': last['close'] * 0.95,
                'reason': 'RSI overbought'
            }
        return None
