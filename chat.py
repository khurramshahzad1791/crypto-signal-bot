import google.generativeai as genai
import config

class TradingChat:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def get_response(self, user_message, recent_signals, trade_history):
        if not self.model:
            return "Chat is disabled. Set GEMINI_API_KEY in Railway variables to enable."
        # Build context
        context = f"""You are a helpful crypto trading assistant. 
Recent signals: {recent_signals}
Recent trades: {trade_history}
User says: {user_message}
Provide a concise, helpful answer in simple English."""
        try:
            response = self.model.generate_content(context)
            return response.text
        except Exception as e:
            return f"Error: {e}"
