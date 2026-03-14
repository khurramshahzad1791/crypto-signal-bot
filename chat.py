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
            # List available models for debugging (visible in Railway logs)
            try:
                models = genai.list_models()
                logger.info("Available models:")
                for m in models:
                    logger.info(f" - {m.name}")
            except Exception as e:
                logger.error(f"Could not list models: {e}")

            # Try common free model names
            model_names = [
                'models/gemini-1.5-flash',
                'gemini-1.5-flash',
                'models/gemini-1.5-pro',
                'gemini-1.5-pro'
            ]
            for model_name in model_names:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    # Quick test
                    self.model.generate_content("test")
                    logger.info(f"Chat using model: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")
                    continue
            if not self.model:
                logger.error("No working Gemini model found.")

    def get_response(self, user_message, recent_signals, trade_history):
        if not self.model:
            return "Chat is disabled or model not available. Check API key and model access in Google AI Studio."
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
