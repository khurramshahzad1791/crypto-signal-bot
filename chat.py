import config

class TradingChat:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY

    def get_response(self, user_message, recent_signals, trade_history):
        if not self.api_key:
            return "Chat is disabled. Set GEMINI_API_KEY in Railway variables to enable."
        # Placeholder – real Gemini integration will be added later
        return f"You said: {user_message}\n\n(Full AI chat coming soon!)"
