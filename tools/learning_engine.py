import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class LearningEngine:
    """ML learning engine - improves from trade outcomes"""
    
    def __init__(self):
        self.model_path = os.getenv('MODEL_PATH', '/app/models/')
        self.trade_history = []
        self.model = self._load_or_create_model()
        
    def _load_or_create_model(self):
        """Load existing model or create new one"""
        model_file = f"{self.model_path}/trading_model.pkl"
        if os.path.exists(model_file):
            try:
                return joblib.load(model_file)
            except:
                return RandomForestClassifier(n_estimators=100)
        return RandomForestClassifier(n_estimators=100)
    
    async def update(self, signals):
        """Update learning from new signals and outcomes"""
        for signal in signals:
            self.trade_history.append({
                'timestamp': signal['timestamp'],
                'features': self._extract_features(signal),
                'outcome': None  # Will be updated when trade closes
            })
        
        # Train if we have enough data
        if len(self.trade_history) >= 100:
            await self.train_models()
    
    async def train_models(self):
        """Train ML models on historical data"""
        try:
            # Prepare training data
            X = []
            y = []
            for trade in self.trade_history[-500:]:  # Last 500 trades
                if trade['outcome'] is not None:
                    X.append(trade['features'])
                    y.append(1 if trade['outcome'] == 'win' else 0)
            
            if len(X) >= 50:
                self.model.fit(X, y)
                
                # Save model
                model_file = f"{self.model_path}/trading_model_{datetime.now().strftime('%Y%m%d')}.pkl"
                joblib.dump(self.model, model_file)
                logger.info(f"Model trained and saved: {model_file}")
                
        except Exception as e:
            logger.error(f"Training error: {e}")
    
    def _extract_features(self, signal):
        """Extract features from signal for ML"""
        return [
            signal['confidence'],
            1 if signal['direction'] == 'LONG' else 0,
            # Add more features as needed
        ]
    
    def predict_outcome(self, signal):
        """Predict probability of success"""
        if len(self.trade_history) < 50:
            return 0.5
        
        features = [self._extract_features(signal)]
        prob = self.model.predict_proba(features)[0][1]
        return prob
