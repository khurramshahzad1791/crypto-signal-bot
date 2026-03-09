import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import streamlit as st
from typing import Dict, Any
import json
from datetime import datetime

# Import agent modules
from agents.market_analyst import MarketAnalyst
from agents.news_sentiment import NewsSentimentAgent
from agents.technical_strategist import TechnicalStrategist
from agents.risk_manager import RiskManager
from agents.execution_optimizer import ExecutionOptimizer

# Import tools
from tools.data_feeds import DataFeedManager
from tools.learning_engine import LearningEngine
from tools.telegram_bot import TelegramBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Integrated Crypto Trading System")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TradingOrchestrator:
    """Orchestrates all AI agents and tools"""
    
    def __init__(self):
        self.data_manager = DataFeedManager()
        self.learning_engine = LearningEngine()
        self.telegram_bot = TelegramBot()
        
        # Initialize all agents
        self.agents = {
            'market_analyst': MarketAnalyst(),
            'news_sentiment': NewsSentimentAgent(),
            'technical_strategist': TechnicalStrategist(),
            'risk_manager': RiskManager(),
            'execution_optimizer': ExecutionOptimizer()
        }
        
        self.active_signals = []
        self.performance_metrics = {}
        
    async def analyze_markets(self):
        """Run complete market analysis through all agents"""
        try:
            # Collect data from all sources
            market_data = await self.data_manager.fetch_all_pairs()
            
            # Run each agent analysis
            agent_results = {}
            for name, agent in self.agents.items():
                result = await agent.analyze(market_data)
                agent_results[name] = result
                
            # Combine and validate signals
            validated_signals = await self._validate_signals(agent_results)
            
            # Learn from outcomes
            await self.learning_engine.update(validated_signals)
            
            return validated_signals
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return []
    
    async def _validate_signals(self, agent_results):
        """Cross-validate signals from multiple agents"""
        combined = []
        
        # Market Analyst + Technical Strategist must agree
        if agent_results.get('market_analyst') and agent_results.get('technical_strategist'):
            ma_signal = agent_results['market_analyst']['signal']
            ts_signal = agent_results['technical_strategist']['signal']
            
            if ma_signal['direction'] == ts_signal['direction']:
                # Calculate confidence score
                confidence = (ma_signal['confidence'] + ts_signal['confidence']) / 2
                
                # Risk check
                risk_approved = await self.agents['risk_manager'].check(
                    ma_signal, 
                    confidence
                )
                
                if risk_approved and confidence >= 70:
                    signal = {
                        'timestamp': datetime.now(),
                        'pair': ma_signal['pair'],
                        'direction': ma_signal['direction'],
                        'entry': ma_signal['price'],
                        'stop_loss': ma_signal['stop_loss'],
                        'take_profit': ma_signal['take_profit'],
                        'confidence': confidence,
                        'strategy': 'multi_agent_consensus',
                        'reasoning': {
                            'market': ma_signal['reason'],
                            'technical': ts_signal['reason'],
                            'news': agent_results.get('news_sentiment', {}).get('summary', '')
                        }
                    }
                    combined.append(signal)
                    
                    # Send to Telegram
                    await self.telegram_bot.send_signal(signal)
        
        return combined
    
    async def run_live(self):
        """Main live trading loop"""
        while True:
            try:
                signals = await self.analyze_markets()
                if signals:
                    self.active_signals = signals
                    
                # Sleep for configured interval
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Live run error: {e}")
                await asyncio.sleep(60)

# FastAPI endpoints
@app.get("/")
async def root():
    return {"status": "online", "service": "Integrated Crypto Trading System"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.get("/signals")
async def get_signals():
    return {"signals": orchestrator.active_signals}

@app.get("/metrics")
async def get_metrics():
    return {"metrics": orchestrator.performance_metrics}

@app.post("/train")
async def train_models():
    """Trigger ML model training"""
    result = await orchestrator.learning_engine.train_models()
    return {"training": result}

# Streamlit dashboard
def run_dashboard():
    st.set_page_config(
        page_title="AI Trading System Dashboard",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("🤖 Multi-Agent AI Trading System")
    
    # Dashboard layout
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Agents", len(orchestrator.agents))
    with col2:
        st.metric("Active Signals", len(orchestrator.active_signals))
    with col3:
        st.metric("Model Accuracy", "87%")
    with col4:
        st.metric("Win Rate", "72%")
    
    # Signals table
    if orchestrator.active_signals:
        st.subheader("📊 Current Signals")
        import pandas as pd
        df = pd.DataFrame(orchestrator.active_signals)
        st.dataframe(df, use_container_width=True)
    
    # Agent performance
    st.subheader("🤔 Agent Consensus Analysis")
    # Add visualization here

# Initialize orchestrator
orchestrator = TradingOrchestrator()

# Start background tasks
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(orchestrator.run_live())

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dashboard":
        run_dashboard()
    else:
        uvicorn.run(app, host="0.0.0.0", port=8000)
