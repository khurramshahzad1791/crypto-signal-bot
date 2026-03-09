import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
from trade_logger import Session, SignalLog
import config

class CryptoScanner:
    def __init__(self):
        self.exchange = ccxt.mexc({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

    def fetch_data(self, symbol, timeframe=config.ENTRY_TIMEFRAME, limit=300):
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None

    def add_indicators(self, df):
        close = df['close']
        high = df['high']
        low = df['low']
        vol = df['volume']

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = close.ewm(span=12).mean()
        exp2 = close.ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # Bollinger Bands
        df['bb_mid'] = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * bb_std
        df['bb_lower'] = df['bb_mid'] - 2 * bb_std

        # EMAs
        df['ema9'] = close.ewm(span=9).mean()
        df['ema21'] = close.ewm(span=21).mean()
        df['ema200'] = close.ewm(span=200).mean()

        # ATR
        tr = pd.concat([high - low,
                        (high - close.shift()).abs(),
                        (low - close.shift()).abs()], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()

        # Volume surge
        df['vol_ma20'] = vol.rolling(20).mean()
        df['vol_surge'] = vol / df['vol_ma20']

        return df

    def detect_regime(self, df):
        # Simplified regime detection (placeholder)
        return "RANGING"

    def mean_reversion_signal(self, df):
        last = df.iloc[-1]
        prev = df.iloc[-2]
        score = 0
        reasons = []

        if last['close'] <= last['bb_lower'] * 1.01:
            score += 20
            reasons.append("near_lower_band")
        if last['close'] >= last['bb_upper'] * 0.99:
            score += 20
            reasons.append("near_upper_band")
        if last['rsi'] < 30:
            score += 15
            reasons.append("oversold")
        if last['rsi'] > 70:
            score += 15
            reasons.append("overbought")
        if last['macd_hist'] > 0 and prev['macd_hist'] < 0:
            score += 10
            reasons.append("macd_bull_cross")
        if last['macd_hist'] < 0 and prev['macd_hist'] > 0:
            score += 10
            reasons.append("macd_bear_cross")

        if score >= 30:
            direction = "LONG" if last['rsi'] < 50 else "SHORT"
            return direction, score, reasons
        return None, None, None

    def breakout_signal(self, df):
        last = df.iloc[-1]
        recent_high = df['high'].iloc[-20:-1].max()
        recent_low = df['low'].iloc[-20:-1].min()
        if last['close'] > recent_high and last['vol_surge'] > 1.5:
            return "LONG", 75, ["breakout_high", f"vol_{last['vol_surge']:.1f}x"]
        if last['close'] < recent_low and last['vol_surge'] > 1.5:
            return "SHORT", 75, ["breakout_low", f"vol_{last['vol_surge']:.1f}x"]
        return None, None, None

    def trend_continuation_signal(self, df):
        last = df.iloc[-1]
        trend_up = last['close'] > last['ema200']
        trend_down = last['close'] < last['ema200']
        near_ema21 = abs(last['close'] - last['ema21']) / last['ema21'] < 0.01
        if trend_up and near_ema21 and last['rsi'] > 40:
            return "LONG", 70, ["pullback_to_ema21", "uptrend"]
        if trend_down and near_ema21 and last['rsi'] < 60:
            return "SHORT", 70, ["pullback_to_ema21", "downtrend"]
        return None, None, None

    def scan_pairs(self):
        results = []
        session = Session()
        for pair in config.PAIRS:
            df = self.fetch_data(pair)
            if df is None or len(df) < 100:
                continue
            df = self.add_indicators(df)
            regime = self.detect_regime(df)

            signals = []
            # Mean reversion
            dir, conf, reasons = self.mean_reversion_signal(df)
            if dir:
                signals.append(('mean_reversion', dir, conf, reasons))
            # Breakout
            dir, conf, reasons = self.breakout_signal(df)
            if dir:
                signals.append(('breakout', dir, conf, reasons))
            # Trend continuation
            dir, conf, reasons = self.trend_continuation_signal(df)
            if dir:
                signals.append(('trend_continuation', dir, conf, reasons))

            if signals:
                best = max(signals, key=lambda x: x[2])
                strategy, direction, confidence, reasons = best
                price = df['close'].iloc[-1]
                atr = df['atr'].iloc[-1]
                if direction == 'LONG':
                    sl = price - atr * 1.5
                    tp = price + atr * 3
                else:
                    sl = price + atr * 1.5
                    tp = price - atr * 3

                # Log signal
                log = SignalLog(
                    pair=pair,
                    signal_type=f"{direction}_{strategy}",
                    price=price,
                    confidence=confidence
                )
                session.add(log)
                session.commit()

                results.append({
                    'pair': pair,
                    'strategy': strategy,
                    'direction': direction,
                    'confidence': confidence,
                    'price': price,
                    'stop_loss': sl,
                    'take_profit': tp,
                    'reasons': ', '.join(reasons),
                    'regime': regime,
                    'timestamp': datetime.now()
                })
        return results
