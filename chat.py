# chat.py
import google.generativeai as genai
import config
from trade_logger import Session, Trade

class TradingChat:
    def __init__(self):
        if config.GEMINI_API_KEY:
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def get_response(self, user_message, recent_signals, trade_history):
        """Generate a chat response using Gemini"""
        if not self.model:
            return "Chat is disabled because GEMINI_API_KEY is not set."

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
