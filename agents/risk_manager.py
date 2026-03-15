class RiskManager:
    async def check(self, signal, account_balance, risk_percent, leverage):
        """Return True if trade is acceptable, and compute position size"""
        stop_distance = abs(signal['price'] - signal['stop_loss'])
        if stop_distance == 0:
            return False, 0
        risk_amount = account_balance * risk_percent
        position_size = risk_amount / stop_distance
        required_margin = position_size / leverage
        # Check if margin is available (simplified)
        if required_margin < account_balance * 0.1:  # 10% max margin per trade
            return True, position_size
        return False, 0
