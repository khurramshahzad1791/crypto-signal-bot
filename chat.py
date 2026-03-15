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
            # Use a model that definitely exists (from your logs)
            model_name = 'models/gemini-2.5-flash'
            try:
                self.model = genai.GenerativeModel(model_name)
                # Quick test
                self.model.generate_content("test")
                logger.info(f"Chat using model: {model_name}")
            except Exception as e:
                logger.error(f"Model {model_name} failed: {e}")
                # Fallback to another model
                fallback = 'models/gemini-flash-latest'
                try:
                    self.model = genai.GenerativeModel(fallback)
                    self.model.generate_content("test")
                    logger.info(f"Chat using fallback model: {fallback}")
                except Exception as e2:
                    logger.error(f"Fallback model also failed: {e2}")
                    self.model = None
        else:
            logger.error("GEMINI_API_KEY not set.")

    def get_response(self, user_message, recent_signals, recent_trades):
        if not self.model:
            return "Chat is temporarily unavailable. Please check logs or try again later."
        signals_text = ""
        if recent_signals:
            signals_text = "Recent signals:\n" + "\n".join(
                [f"- {s['pair']} {s['direction']} at {s['price']:.2f} (confidence {s['confidence']}%)"
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
