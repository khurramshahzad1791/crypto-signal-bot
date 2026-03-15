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
        if os.path.exists(self.model_path + 'model.pkl'):
            try:
                self.model = joblib.load(self.model_path + 'model.pkl')
            except:
                self.model = None

    def prepare_training_data(self):
        """Fetch historical signals and their outcomes to create a dataset."""
        session = Session()
        # Get trades from last 90 days
        cutoff = datetime.utcnow() - timedelta(days=90)
        trades = session.query(Trade).filter(Trade.timestamp >= cutoff).all()
        if len(trades) < 20:
            return None, None  # Not enough data

        # Feature engineering: use signal features and outcome
        data = []
        for t in trades:
            # Simple features: confidence, maybe direction encoded
            features = {
                'confidence': t.confidence,
                'direction_long': 1 if 'LONG' in t.signal_type else 0,
                'pair_encoded': hash(t.pair) % 10,  # simple encoding
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
        # Train LightGBM
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
        # Save model
        os.makedirs(config.MODEL_PATH, exist_ok=True)
        joblib.dump(self.model, config.MODEL_PATH + 'model.pkl')
        print(f"Model trained and saved to {config.MODEL_PATH}model.pkl")

    def predict_win_probability(self, signal):
        """Predict win probability for a new signal."""
        if self.model is None:
            return 0.5
        # Create feature vector (must match training)
        features = [[
            signal['confidence'],
            1 if 'LONG' in signal.get('direction','') else 0,
            hash(signal['pair']) % 10
        ]]
        prob = self.model.predict(features)[0]
        return prob
