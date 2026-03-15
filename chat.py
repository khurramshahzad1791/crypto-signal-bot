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
            # Correct model name for free tier (as of 2025)
            model_name = 'models/gemini-1.5-flash'
            try:
                self.model = genai.GenerativeModel(model_name)
                # Quick test to confirm it works
                response = self.model.generate_content("test")
                if response and response.text:
                    logger.info(f"Chat using model: {model_name} – success")
                else:
                    logger.error("Model test returned empty response")
                    self.model = None
            except Exception as e:
                logger.error(f"Model initialization failed: {e}")
                # Optionally list available models for debugging
                try:
                    models = genai.list_models()
                    logger.info("Available models that support generateContent:")
                    for m in models:
                        if 'generateContent' in m.supported_generation_methods:
                            logger.info(f" - {m.name}")
                except Exception as list_err:
                    logger.error(f"Could not list models: {list_err}")
                self.model = None
        else:
            logger.error("GEMINI_API_KEY not set.")

    def get_response(self, user_message, recent_signals, recent_trades):
        if not self.model:
            return "Chat is disabled. Check your Gemini API key and model availability in Google AI Studio."
        # Build context
        signals_text = ""
        if recent_signals:
            signals_text = "Recent signals:\n" + "\n".join(
                [f"- {s['pair']} {s['direction']} at {s['price']:.2f} (confidence {s['confidence']}%) – {s.get('reasons','')}"
                 for s in recent_signals]
            )
        else:
            signals_text = "No recent signals."

        trades_text = ""
        if recent_trades:
            trades_text = "Recent trades:\n" + "\n".join(
                [f"- {t.pair} {t.signal_type} entry {t.entry_price:.2f} exit {t.exit_price if t.exit_price else 'open'} P&L {t.pnl_percent or 0:.1f}%"
                 for t in recent_trades]
            )
        else:
            trades_text = "No trade history yet."

        prompt = f"""You are a professional crypto trading assistant. You have access to real-time market signals and trade history.

{signals_text}
{trades_text}

The user asks: {user_message}

Provide a concise, helpful answer in simple English. If the user asks about a specific pair or trade, use the context. If they ask for a recommendation, base it on the recent signals."""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {e}"
