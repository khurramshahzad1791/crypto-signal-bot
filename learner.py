import os
import joblib
import config

class StrategyLearner:
    def __init__(self):
        self.model_path = config.MODEL_PATH
        self.model = None
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
            except:
                self.model = None

    def train(self):
        # Placeholder – ML training will be added later
        print("Training disabled in this version.")
        pass
