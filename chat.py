import google.generativeai as genai
import config
import logging

logger = logging.getLogger(__name__)

class TradingChat:
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.model = None
        if self.api_key:
            genai.configure(api_key=self.api_key)
            model_name = 'models/gemini-1.5-flash'
            try:
                self.model = genai.GenerativeModel(model_name)
                # Quick test
                self.model.generate_content("test")
                logger.info(f"Chat using model: {model_name}")
            except Exception as e:
                logger.error(f"Model initialization failed: {e}")
                self.model = None
        else:
            logger.error("GEMINI_API_KEY not set.")

    def get_response(self, user_message, recent_signals, recent_trades):
        if not self.model:
            return "Chat is disabled. Check your Gemini API key in Railway Variables."
        signals_text = "\n".join([f"{s['pair']} {s['direction']} at {s['price']}" for s in recent_signals]) if recent_signals else "No recent signals."
        trades_text = "\n".join([f"{t.pair} {t.outcome}" for t in recent_trades]) if recent_trades else "No trade history."
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
