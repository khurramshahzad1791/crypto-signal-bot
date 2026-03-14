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
            # Log available models for debugging (optional)
            try:
                models = genai.list_models()
                logger.info("Available models that support generateContent:")
                for m in models:
                    if 'generateContent' in m.supported_generation_methods:
                        logger.info(f" - {m.name}")
            except Exception as e:
                logger.error(f"Could not list models: {e}")

            # Try models from your logs that are likely free and work
            model_candidates = [
                'models/gemini-flash-lite-latest',
                'models/gemini-2.0-flash',
                'models/gemini-pro-latest',
                'models/gemini-2.0-flash-001',
                'models/gemini-2.0-flash-lite',
                'models/gemini-2.5-flash',
                'models/gemini-3-flash-preview',
                'models/gemma-3-12b-it',
            ]
            for model_name in model_candidates:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    # Quick test
                    response = self.model.generate_content("Say 'test'")
                    if response and response.text:
                        logger.info(f"Chat using model: {model_name} – success")
                        break
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")
                    self.model = None
                    continue
            if not self.model:
                logger.error("No working Gemini model found.")
        else:
            logger.error("GEMINI_API_KEY not set.")

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
