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
        self.model_path = os.path.join(config.MODEL_PATH, 'model.pkl')
        self.model = None
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
            except:
                self.model = None

    def prepare_training_data(self):
        """Fetch historical signals and their outcomes."""
        session = Session()
        cutoff = datetime.utcnow() - timedelta(days=90)
        trades = session.query(Trade).filter(Trade.timestamp >= cutoff).all()
        if len(trades) < 20:
            return None, None

        data = []
        for t in trades:
            # Simple features
            features = {
                'confidence': t.confidence,
                'direction_long': 1 if 'LONG' in t.signal_type else 0,
                'pair_encoded': hash(t.pair) % 10,
                'outcome': 1 if t.outcome == 'win' else 0
            }
            data.append(features)
        df = pd.DataFrame(data)
        X = df[['confidence', 'direction_long', 'pair_encoded']]
        y = df['outcome']
        return X, y

    def train(self):
        X, y = self.prepare_training_data()
        if X is None:
            print("Not enough data to train yet. Need at least 20 trades.")
            return
        train_data = lgb.Dataset(X, label=y)
        params = {
            'objective': 'binary',
            'metric': 'binary_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 10,
            'learning_rate': 0.05,
            'feature_fraction': 0.9
        }
        self.model = lgb.train(params, train_data, num_boost_round=50)
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        print(f"Model trained and saved to {self.model_path}")

    def predict_win_probability(self, signal):
        if self.model is None:
            return 0.5
        features = [[
            signal['confidence'],
            1 if 'LONG' in signal.get('direction','') else 0,
            hash(signal['pair']) % 10
        ]]
        prob = self.model.predict(features)[0]
        return prob
