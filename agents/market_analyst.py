import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MarketAnalyst:
    """Market data analysis agent - fetches and analyzes price data"""
    
    def __init__(self):
        self.exchange = ccxt.mexc({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        
    async def analyze(self, market_data):
        """Analyze market conditions and generate signals"""
        try:
            signals = []
            for pair in market_data['pairs']:
                df = market_data[pair]
                
                # Calculate indicators
                df = self._add_indicators(df)
                
                # Generate signal
                signal = self._generate_signal(df, pair)
                if signal:
                    signals.append(signal)
                    
            return {
                'agent': 'market_analyst',
                'signals': signals,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Market analyst error: {e}")
            return {'signal': None, 'confidence': 0}
    
    def _add_indicators(self, df):
        """Add technical indicators"""
        close = df['close']
        high = df['high']
        low = df['low']
        
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
        
        # Bollinger Bands
        df['bb_mid'] = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * bb_std
        df['bb_lower'] = df['bb_mid'] - 2 * bb_std
        
        # EMAs
        df['ema9'] = close.ewm(span=9).mean()
        df['ema21'] = close.ewm(span=21).mean()
        df['ema200'] = close.ewm(span=200).mean()
        
        return df
    
    def _generate_signal(self, df, pair):
        """Generate trading signal from indicators"""
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Mean reversion signal
        if last['close'] <= last['bb_lower'] * 1.01 and last['rsi'] < 30:
            return {
                'pair': pair,
                'direction': 'LONG',
                'price': last['close'],
                'confidence': 85,
                'stop_loss': last['close'] * 0.98,
                'take_profit': last['close'] * 1.05,
                'reason': 'Oversold bounce at lower band'
            }
        
        # Breakout signal
        recent_high = df['high'].iloc[-20:-1].max()
        if last['close'] > recent_high and last['volume'] > df['volume'].mean() * 1.5:
            return {
                'pair': pair,
                'direction': 'LONG',
                'price': last['close'],
                'confidence': 80,
                'stop_loss': last['close'] * 0.97,
                'take_profit': last['close'] * 1.08,
                'reason': 'Breakout with volume'
            }
        
        return None
