import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MarketAnalyst:
    def __init__(self):
        self.exchange = ccxt.mexc({'enableRateLimit': True})
        self.pairs = ["BTC/USDT", "ETH/USDT", "XRP/USDT", "SOL/USDT"]

    async def analyze(self):
        signals = []
        for pair in self.pairs:
            try:
                df = self.fetch_ohlcv(pair, '5m', 200)
                if df is None:
                    logger.warning(f"Could not fetch data for {pair}")
                    continue
                df = self.add_indicators(df)
                signal = self.generate_signal(pair, df)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error analyzing {pair}: {e}")
        logger.info(f"Market analyst generated {len(signals)} signals")
        return signals

    def fetch_ohlcv(self, symbol, timeframe, limit):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Fetch error for {symbol}: {e}")
            return None

    def add_indicators(self, df):
        close = df['close']
        high = df['high']
        low = df['low']
        vol = df['volume']

        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        df['bb_mid'] = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * bb_std
        df['bb_lower'] = df['bb_mid'] - 2 * bb_std

        df['ema9'] = close.ewm(span=9).mean()
        df['ema21'] = close.ewm(span=21).mean()
        df['ema200'] = close.ewm(span=200).mean()

        tr = pd.concat([high - low,
                        (high - close.shift()).abs(),
                        (low - close.shift()).abs()], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()

        df['vol_ma20'] = vol.rolling(20).mean()
        df['vol_surge'] = vol / df['vol_ma20']

        return df

    def generate_signal(self, pair, df):
        last = df.iloc[-1]
        prev = df.iloc[-2]
        reasons = []
        confidence = 50
        strategy = None

        # Mean Reversion
        if last['close'] <= last['bb_lower'] and last['rsi'] < 30:
            direction = 'LONG'
            confidence = 75
            reasons.append('oversold bounce')
            strategy = 'mean_reversion'
        elif last['close'] >= last['bb_upper'] and last['rsi'] > 70:
            direction = 'SHORT'
            confidence = 75
            reasons.append('overbought rejection')
            strategy = 'mean_reversion'
        # Breakout
        elif last['vol_surge'] > 1.5 and last['close'] > df['high'].iloc[-20:-1].max():
            direction = 'LONG'
            confidence = 80
            reasons.append('breakout with volume')
            strategy = 'breakout'
        elif last['vol_surge'] > 1.5 and last['close'] < df['low'].iloc[-20:-1].min():
            direction = 'SHORT'
            confidence = 80
            reasons.append('breakdown with volume')
            strategy = 'breakout'
        # Trend continuation
        elif last['close'] > last['ema200'] and abs(last['close'] - last['ema21']) / last['ema21'] < 0.01:
            direction = 'LONG'
            confidence = 70
            reasons.append('pullback to EMA21 in uptrend')
            strategy = 'trend_continuation'
        elif last['close'] < last['ema200'] and abs(last['close'] - last['ema21']) / last['ema21'] < 0.01:
            direction = 'SHORT'
            confidence = 70
            reasons.append('pullback to EMA21 in downtrend')
            strategy = 'trend_continuation'
        else:
            return None

        atr = last['atr']
        if direction == 'LONG':
            sl = last['close'] - atr * 1.5
            tp = last['close'] + atr * 3
        else:
            sl = last['close'] + atr * 1.5
            tp = last['close'] - atr * 3

        return {
            'pair': pair,
            'direction': direction,
            'strategy': strategy,
            'price': last['close'],
            'confidence': confidence,
            'stop_loss': sl,
            'take_profit': tp,
            'reasons': ', '.join(reasons),
            'timestamp': datetime.now()
        }
