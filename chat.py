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
        signals_text = "\n".join([f"{s['pair']} {s['direction']} at {s['price']}" for s in recent_signals]) if recent_signals else "No recent signals."
        trades_text = "\n".join([f"{t['pair']} {t['outcome']}" for t in trade_history]) if trade_history else "No trade history."
        prompt = f"""You are a helpful crypto trading assistant.
Recent signals:
{signals_text}
Recent trades:
{trades_text}
User asks: {user_message}
Answer concisely in simple English."""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {e}"
