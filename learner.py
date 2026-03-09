# learner.py
import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
from trade_logger import Session, Trade, SignalLog
import config
import os
from datetime import datetime, timedelta

class StrategyLearner:
    def __init__(self):
        self.model_path = config.MODEL_PATH
        self.model = None
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)

    def prepare_training_data(self):
        """Collect past signals and their outcomes to create a dataset."""
        session = Session()
        # Get trades from last 90 days
        cutoff = datetime.utcnow() - timedelta(days=90)
        trades = session.query(Trade).filter(Trade.timestamp >= cutoff).all()
        if len(trades) < 50:
            return None, None  # Not enough data yet

        # Feature engineering
        data = []
        for t in trades:
            # Features: signal type, confidence, market regime at entry, etc.
            features = {
                'confidence': t.confidence,
                'signal_type': t.signal_type,
                'pair': t.pair,
                'entry_price': t.entry_price,
                'stop_loss': t.stop_loss,
                'take_profit': t.take_profit,
                'outcome': 1 if t.outcome == 'win' else 0
            }
            data.append(features)
        df = pd.DataFrame(data)
        # One‑hot encode categoricals
        df = pd.get_dummies(df, columns=['signal_type', 'pair'])
        X = df.drop(['outcome', 'entry_price', 'stop_loss', 'take_profit'], axis=1)
        y = df['outcome']
        return X, y

    def train(self):
        X, y = self.prepare_training_data()
        if X is None:
            print("Not enough data to train yet.")
            return
        # Train LightGBM
        train_data = lgb.Dataset(X, label=y)
        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9
        }
        self.model = lgb.train(params, train_data, num_boost_round=100)
        joblib.dump(self.model, self.model_path)
        print(f"Model trained and saved to {self.model_path}")

    def predict_win_probability(self, signal):
        """Predict win probability for a new signal."""
        if self.model is None:
            return 0.5  # default
        # Construct feature vector (must match training columns)
        # This is simplified – in production you'd need consistent column alignment.
        # We'll implement a robust version in next iteration.
        return 0.5
