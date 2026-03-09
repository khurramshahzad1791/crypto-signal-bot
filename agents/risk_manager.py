class RiskManager:
    async def check(self, signal, confidence):
        # Simple risk check: always approve for now
        return True
