import streamlit as st
import asyncio
import logging
from fastapi import FastAPI
import uvicorn
import threading
import time
from datetime import datetime
import pandas as pd
import traceback
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from agents.market_analyst import MarketAnalyst
from agents.news_sentiment import NewsSentimentAgent
from agents.technical_strategist import TechnicalStrategist
from agents.risk_manager import RiskManager
from agents.execution_optimizer import ExecutionOptimizer
from chat import TradingChat
from trade_logger import Session, Trade, SignalLog
from learner import StrategyLearner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Multi-Agent Trading System")

@app.get("/")
async def root():
    return {"status": "online", "service": "Trading System"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

class PaperTrade:
    """Represents an open paper trade"""
    def __init__(self, signal, db_session):
        self.signal = signal
        self.entry_time = signal['timestamp']
        self.entry_price = signal['price']
        self.direction = signal['direction']
        self.stop_loss = signal['stop_loss']
        self.take_profit = signal['take_profit']
        self.pair = signal['pair']
        self.confidence = signal['confidence']
        self.strategy = signal.get('strategy', 'unknown')
        self.status = 'open'
        self.db_session = db_session
        # Create database record
        trade = Trade(
            pair=self.pair,
            signal_type=f"{self.direction}_{self.strategy}",
            entry_price=self.entry_price,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            confidence=self.confidence,
            outcome='open'
        )
        db_session.add(trade)
        db_session.commit()
        self.db_id = trade.id

    def check_exit(self, current_price):
        """Check if TP or SL hit, return outcome if closed"""
        if self.direction == 'LONG':
            if current_price >= self.take_profit:
                return 'win', self.take_profit
            elif current_price <= self.stop_loss:
                return 'loss', self.stop_loss
        else:  # SHORT
            if current_price <= self.take_profit:
                return 'win', self.take_profit
            elif current_price >= self.stop_loss:
                return 'loss', self.stop_loss
        return None, None

    def close(self, outcome, exit_price):
        """Close the trade and update database"""
        pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        if self.direction == 'SHORT':
            pnl_pct = -pnl_pct  # invert for short
        # Update database
        trade = self.db_session.query(Trade).filter_by(id=self.db_id).first()
        trade.exit_price = exit_price
        trade.outcome = outcome
        trade.pnl_percent = round(pnl_pct, 2)
        self.db_session.commit()
        self.status = outcome
        logger.info(f"Closed {self.pair} {self.direction} at {exit_price} for {outcome} ({pnl_pct:.2f}%)")

2f}%)")

classclass TradingOrchestrator:
 TradingOrchestrator:
    def    def __init__(self __init__(self):
       ):
        self. self.agents =agents = {
            'market {
            'market_anal_analyst': Marketyst': MarketAnalAnalyst(),
yst(),
            '            'news_snews_sentimententiment': News': NewsSentimentSentimentAgent(),
            'Agent(),
            'technical_strtechnical_strategist': TechnicalStrategist(),
           ategist': TechnicalStrategist(),
            'risk_manager': 'risk_manager': RiskManager RiskManager(),
           (),
            'execution_ 'execution_optimizeroptimizer': Execution': ExecutionOptimizerOptimizer()
       ()
        }
        }
        self. self.learnerlearner = StrategyLearner = StrategyLearner()
       ()
        self.sign self.signals =als = [] []                   # live # live signals ( signals (not necessarilynot necessarily opened)
        self.open_pos opened)
        self.open_positions =itions = []   []   # list # list of Paper of PaperTrade objectsTrade objects
       
        self.r self.running = True
unning = True
        self        self.last_scan_time = None.last_scan_time = None
       
        self.sc self.scan_countan_count =  = 0
        self.status_message = "Initializing..."
       0
        self.status_message = "Initializing..."
        self.last self.last_error =_error = None
        self None
        self.lock.lock = threading.Lock = threading.Lock()
        self.last()
        self.last_training = None_training = None
        self.db
        self.db_session = Session()

_session = Session()

    async    async def run def run_cycle_cycle(self):
(self):
        try        try:
            self.status:
            self.status_message =_message = "Scan "Scanning marketsning markets..."
           ..."
            self.last_error = self.last None
_error = None
            market            market_signals = await_signals self. = await self.agents['agents['market_market_analystanalyst'].analy'].analyze()
ze()
            logger.info(f"Market            logger.info(f"Market analyst returned analyst returned {len {len(market_signals(market_signals) if) if market_sign market_signals elseals else 0 0} signals} signals")

            # Check")

            # Check open positions open positions for exits for exits
           
            still_open = still_open = []
            []
            for pos for pos in self.open_pos in self.open_positions:
itions:
                # Get current                # Get current price for price for the pair the pair (sim (simplified – useplified – use the the market analyst market analyst's fetch's fetch)
               )
                df = self.agents[' df = self.agents['market_analystmarket_analyst'].fetch'].fetch_ohl_ohlcv(pos.paircv(pos.pair, ', '1m1m', 1)
', 1)
                if                if df is df is not None:
                    not None:
                    current_price current_price = df = df['['close'].iloc[-close'].iloc[-1]
                    outcome, exit1]
                    outcome, exit_price = pos.check_price = pos.check_exit_exit(current_price(current_price)
                   )
                    if outcome if outcome:
                        pos.close:
                        pos.close(outcome(outcome, exit, exit_price)
_price)
                    else                    else:
                        still_open.append(pos)
               :
                        still_open.append(pos)
                else:
                    still else:
                    still_open.append_open.append(pos)(pos)  #  # keep if keep if can can't fetch't fetch price price
            self.open
            self.open_positions = still_positions = still_open

           _open

            # # Open new trades Open new trades from signals from signals ( (if highif high confidence and confidence and not already in position for that pair)
 not already in position for that pair)
            if market_sign            if market_signals:
als:
                with                with self.lock:
 self.lock:
                    for                    for signal in signal in market_sign market_signals:
                        # Skip ifals:
                        # Skip if already in already in an an open position open position for this pair
 for this pair
                        if                        if any(pos any(pos.pair.pair == == signal[' signal['pair'] forpair'] for pos in pos in self.open self.open_positions_positions):
                           ):
                            continue
                        # continue
 Only                        # Only take take signals with confidence signals with confidence >=  >= 70
                        if70
                        if signal[' signal['confidence']confidence'] <  < 70:
                            continue70:
                            continue
                       
                        # Add # Add ML probability ML probability
                       
                        ml_prob = self ml_prob = self.learner.predict.learner.predict_win_win_probability_probability(signal)
(signal)
                        signal['                        signal['ml_probml_prob'] = round('] = round(ml_prob, 2)
ml_prob, 2)
                        # Optionally adjust confidence
                                               # Optionally adjust confidence
                        signal[' signal['confidence']confidence'] = int((signal = int((signal['confidence'] +['confidence'] + ml_prob ml_prob * 100) * 100) / 2)

                        # / 2)

                        # Open paper Open paper trade
                        trade trade
                        trade = Paper = PaperTrade(sTrade(signal,ignal, self.db self.db_session)
_session)
                        self.open_positions.append                        self.open_positions.append(trade(trade)
                        logger.info)
                        logger.info(f(f""Opened paper tradeOpened paper trade: {: {signal['pair']signal['pair']} {} {signal['signal['direction']direction']} at {signal['price']}")

                    # Store} at {signal['price']}")

                    # Store all signals for UI (optional all signals for UI (optional)
                   )
                    self.signals.extend self.signals.extend(market(market_signals_signals)
                   )
                    self.sc self.scan_count += lenan_count += len(market(market_signals)

                self.status_signals)

                self.status_message = f"Last scan_message = f"Last scan: {datetime.now: {datetime.now().strftime('%().strftime('%H:%M:%H:%M:%S')}S')} – – {len(market {len(market_signals_signals)} signals)} signals, {len(self.open_pos, {len(self.open_positions)}itions)} open positions."
            else:
 open positions."
            else:
                self                self.status_message = f"Last.status_message = f"Last scan: scan: {datetime.now {datetime.now().().strftime('%Hstrftime('%H:%M:%S')}:%M:%S')} – No – No signals, signals, {len(self.open {len(self.open_positions_positions)} open)} open positions."

            self positions."

            self.last_.last_scan_time = datetimescan_time.now()

 = datetime.now()

            #            # Auto-retrain once Auto-retrain once per day per day

            if self.last_t            if self.last_training is None or (datetime.now() - selfraining is None or (datetime.now() - self.last_training)..last_training).total_seconds()total_seconds() > 86400:
                threading.Thread > 86400:
                threading.Thread(target=self.lear(target=self.learner.trainner.train).start).start()
                self.last()
               _training self.last_training = datetime = datetime.now()

        except.now()

        except Exception as Exception as e:
            error e:
            error_trace_trace = trace = traceback.format_excback.format_exc()
           ()
            logger.error(f" logger.error(f"Cycle errorCycle error: {e}\: {e}\n{n{error_trace}")
error_trace}")
            self            self.last_error.last_error = str(e)
            self.status_message = str(e)
            self.status_message = f"Error = f"Error in scan in scan: {str(e: {str(e)})}"

"

    async def run    async def run_fore_forever(selfver(self):
       ):
        while self while self.running:
           .running:
            await self.run_ await self.run_cycle()
cycle()
            await asyn            await asyncio.sleep(300)cio.sleep(300)   #  # 5 minutes

background5 minutes

background_thread_started =_thread_started = False

 False

def start_background_loopdef start_background_loop(orche(orchestratorstrator_ref):
_ref):
    try:
           try:
        loop = loop = asyn asyncio.new_event_cio.new_event_loop()
loop()
        asyn        asynciocio.set_event.set_event_loop_loop(loop)
       (loop)
        loop.run_until_complete loop.run_until_complete(orche(orchestrstrator_ref.runator_ref.run_fore_forever())
    exceptver())
    except Exception as Exception as e:
 e:
        logger.error(f        logger.error(f"Background"Background thread crashed: {e}", thread crashed: {e}", exc_info exc_info=True)

def main():
    global background=True)

def main():
    global background_thread_start_thread_started

    sted

    st.set_page_config(page.set_page_config(page_title="_title="AI Trading System",AI Trading System", layout=" layout="wide")
    stwide")
    st.title("🤖.title("🤖 Autonomous AI Autonomous AI Trading System Trading System")

    if 'orche")

    if 'orchestratorstrator' not' not in st.session_state:
        in st.session_state:
        st.session st.session_state.orchestrator =_state.orchestrator = TradingOrche TradingOrchestrator()
strator()
        if        if not background_thread_started:
 not background_thread_started:
            thread            thread = threading = threading.Thread(
                target.Thread(
                target=start=start_background_background_loop,
               _loop,
                args=( args=(st.sessionst.session_state.orchestr_state.orchestrator,ator,),
               ),
                daemon=True
 daemon            )
            thread.start()
=True
            )
            thread.start()
            background            background_thread_started =_thread_started = True
            logger True
.info("            logger.info("Background threadBackground thread started.")

 started.")

    orch = st    orch = st.session_state.orchestrator.session_state.orchestrator

    # Side

    # Sidebar status
    with st.sidebar status
    with st.sidebar:
bar:
        st.header("        st.header("SystemSystem Status Status")
       ")
        st.write st.write(f"Agents(f"Agents active: active: {len {len(orch.agents)}")
        st.write(f"Total signals generated: {len(orch.sign(orch.agents)}")
        st.write(f"Total signals generated: {len(orch.signals)}")
        st.writeals)}")
        st.write(f"(f"Open positionsOpen positions: {len(: {orch.openlen(orch.open_positions_positions)}")
)}")
        st.write(f        st"Last.write(f"Last scan: scan: {orch {orch.last_scan_time.strftime('%H:%M:%S.last_scan_time.strftime('%H:%M:%S') if') if orch.last orch.last_scan_time else 'Never'}")
        st_scan_time else 'Never'}")
        st.write(f"Status: {orch.status_message}")
       .write(f"Status: {orch.status_message}")
        if orch.last_error:
 if orch.last_error:
            st            st.error(f.error(f"Last error: {orch"Last error: {orch.last_error}")

        st.sidebar.header(".last_error}")

        st.sidebar.header("Account Settings")
       Account Settings")
 account        account_balance = st.side_balance = st.sidebar.number_input("Account Balancebar.number_input("Account Balance (USDT (USDT)", value=1000)", value=1000, step=100, step=)
        risk_percent =100)
        risk_percent = st.sidebar.slider(" st.sidebar.slider("Risk per trade (%)Risk per trade (%)", ", 0.0.5, 55, 5.0.0, , 2.0) / 2.0) / 100
100
        leverage = st        leverage = st.side.sidebar.selectbar.selectbox("Leverbox("Leverage (for info)", [1, age (for info)", [1, 5,5, 10, 10, 20, 20, 50 50, 100],, 100], index= index=5)

5)

    # Tabs    # Tabs
   
    tab1 tab1, tab2,, tab2, tab3 tab3, tab, tab4, tab5, tab6 = st.t4, tab5, tab6 = st.tabs([
abs([
        "        "📡📡 Live Signals", " Live Signals", "📊📊 Open Positions Open Positions", "📈 Performance", "💬 Chat", "", "📈 Performance", "💬 Chat", "📉📉 Chart", Chart", "🤖 Agent "🤖 Agent Chat"
 Chat"
    ]    ])

)

    with tab    with tab1:
1:
        st        st.sub.subheaderheader("Latest Signals")
        if("Latest Signals")
        if orch.signals:
            df = pd.DataFrame( orch.signals:
            df = pd.DataFrame(orch.signals[-50:][::-1])
            # Add position sizeorch.signals[-50:][::-1])
            # Add position size column column for info
 for info
            def            def compute compute_size_size(row):
                stop_dist =(row):
                stop_dist = abs abs(row(row['price'] -['price'] - row[' row['stop_loss'])
               stop_loss'])
                if stop if stop_dist ==_dist == 0 0:
                   :
                    return 0
                risk_amount = return 0
                risk_amount = account_balance * risk_percent
                pos account_balance * risk_percent
                pos_size =_size = risk_amount / stop risk_amount / stop_dist
_dist
                return round(pos                return round(pos_size,_size, 2)
            2)
            df['position_size'] = df.apply(compute_size, df['position_size'] = df.apply(compute_size, axis=1)
 axis=1)
            st            st.dataframe(df, use_container_width=True)
        else:
.dataframe(df, use_container_width=True)
        else:
            st            st.info.info("No signals yet. Waiting for market analysis("No signals yet. Waiting for market analysis...")

...")

    with    with tab2:
        st.subheader(" tab2:
        st.subheader("Open Paper Trades")
        if orch.open_positionsOpen Paper Trades")
        if orch.open_positions:
            data = []
            for pos in orch.open_positions:
:
            data = []
            for pos in orch.open_positions:
                # get current price
                df = orch.agents['market_                # get current price
                df = orch.agents['market_analyst'].fetchanalyst_ohl'].fetch_ohlcv(pos.paircv(pos.pair, '1m', , '1m', 1)
                current = df['close'].1)
                current = df['close'].ilociloc[-1] if df is not None else '[-1] if df is not None else 'N/AN/A'
                data.append({
                    ''
                data.append({
                    'Pair': pos.pair,
                    'Pair': pos.pair,
                    'Direction':Direction': pos.d pos.direction,
                    'irection,
                    'Entry': pos.entry_price,
                    'Current': currentEntry': pos.entry_price,
                    'Current': current,
,
                    'SL': pos                    'SL': pos.stop_loss,
                    'TP.stop_loss,
                    'TP': pos': pos.take_profit.take_profit,
                    'P&L,
                    'P&L %': f %': f"{"{((current - pos((current - pos.entry_price)/.entry_price)/pos.entry_price*100):.2f}" if current != 'pos.entry_price*100):.2f}" if current != 'N/A' else 'NN/A' else 'N/A'
                })
            df = pd.DataFrame(data/A'
                })
            df = pd.DataFrame(data)
            st.dataframe(df)
            st.dataframe(df, use_container_width=True)
        else:
           , use_container_width=True)
        else:
            st.info st.info("No("No open positions.")

    open positions.")

    with tab with tab3:
3:
        st.sub        st.subheaderheader("Performance Analytics("Performance Analytics")
        db_session")
        db = Session_session = Session()
       ()
        trades = trades = db_session.query(T db_session.query(Trade).rade).order_byorder_by(Trade.timestamp(Trade.timestamp.desc.desc()).limit(100).all()
        if trades:
           ()).limit(100).all()
        if trades:
            df_trades = pd.DataFrame([{
 df_trades = pd.DataFrame([{
                'time': t.timestamp,
                '                'time': t.timestamp,
                'pair': t.ppair': t.pair,
air,
                'signal': t.signal_type,
                'entry': t.entry_price,
                '                'signal': t.signal_type,
                'entry': t.entry_price,
                'exit': t.exit_price,
                'pnl%': t.pnl_percent,
                'outcome':exit': t.exit_price,
                'pnl%': t.pnl_percent,
                'outcome': t.outcome
 t.outcome
            } for t in            } for t in trades])
            st.dataframe(df_trades, use_container trades])
            st.dataframe(df_trades, use_container_width=True_width=True)

            wins =)

            wins = df_t df_trades[df_trades['outcome'] == 'win']
           rades[df_trades['outcome'] == 'win']
            losses losses = df_trades[df = df_trades_t[df_trades['outcomerades['outcome'] =='] == 'loss']
            'loss']
            win_rate win_rate = len(wins) / (len(wins) + len(losses = len(wins) / (len(wins) + len(losses)) * 100 if len(wins)+len)) * 100 if len(wins)+len(losses)(losses) >  > 0 else 0
            total_pnl =0 else 0
            total_pnl = df_t df_trades['pnl%'].sum() if 'pnlrades['pnl%'].sum() if 'pnl%'%' in df_trades else  in df_trades else 0
0
            col            col1,1, col2 col2, col3 = st.columns, col3 = st.columns(3)
           (3)
            col1 col1.metric("Win Rate", f"{.metric("Win Rate", f"{win_rate:.1fwin_rate:.1f}%")
            col}2.metric("Total P&L%")
            col2.metric("Total P&L %", f"{total_pnl:. %", f"{total_pnl:.2f}%")
            col3.metric("Total Trades", len(df_trades))

            if2f}%")
            col3.metric("Total Trades", len(df_trades))

 'pn            if 'pnl%l%' in' in df_trades and not df_trades.empty:
                df_trades['cumulative'] = df df_trades and not df_trades.empty:
                df_trades['cumulative'] = df_trades['pnl%_trades['pnl%'].cum'].cumsum()
sum()
                fig = go.Figure()
                fig.add_trace                fig = go.Figure()
                fig.add_trace(go(go.Scatter(x=df_trades['time'],.Scatter(x=df_trades['time'], y= y=df_trades['cumulative'],
                                          mode='lines', name='Equity Curve'))
                fig.update_layoutdf_trades['cumulative'],
                                          mode='lines', name='Equity Curve'))
                fig.update_layout(title(title='Equity='Equity Curve ( Curve (CumCumulative Pulative P&L&L %)')
 %)')
                st.plotly_chart                st.plotly_chart(fig(fig,, use use_container_width=True)
        else:
            st.info_container_width=True)
        else:
            st.info("No trades yet. The system will start paper trading automatically.")

    with("No trades yet. The system will start paper trading automatically.")

    with tab4:
        st.subheader("AI Chat Assistant")
 tab4:
        st.subheader("AI Chat Assistant")
        if        if 'chat' not in st 'chat' not in st.session_state:
            st.session_state.chat = TradingChat()

       .session_state:
            st.session_state.chat = TradingChat()

        user_input user_input = st.text_input("You = st.text_input("You:", key:", key="chat_input")
="chat        if st.button("Send_input")
        if st.button("Send"):
"):
            if user            if user_input:
_input:
                recent_sign                recent_signalsals = orch = orch.signals[-5:] if.signals[-5:] if orch.signals else []
                db_session orch.signals else []
                db_session = Session = Session()
                recent_trades =()
                recent_trades = db_session db_session.query(T.query(Trade).rade).order_byorder_by(Trade.timestamp.desc()).limit((Trade.timestamp.desc()).limit(55).all()
                response =).all()
                response = st.session st.session_state.chat.get_state.chat.get_response(user_response(user_input_input,, recent_sign recent_signals, recent_tals, recent_tradesrades)
)
                st.text_area                st.text_area("Assistant("Assistant:", response:", response, height=200, height=200)

    with tab)

    with tab5:
5:
        st        st.subheader("Interactive.subheader("Interactive Chart Analysis Chart Analysis")
       ")
        col1 col1, col2 = st.columns([1, col2 = st.columns([1, 3])
, 3])
        with        with col1 col1:
            chart_pair:
            chart_pair = st.selectbox("Select Pair", orch. = st.selectbox("Select Pair", orch.agents['market_analystagents['market_analyst'].p'].pairs)
airs)
            chart_days            chart_days = st = st.sl.slider("Days of history", 1, 30, 7)
            show_support = st.checkbox("Showider("Days of history", 1, 30, 7)
            show_support = st.checkbox("Show Support/Resistance", Support/Resistance", True)
 True)
            show_trend            show_trendlines =lines = st.check st.checkbox("Show Trendbox("Show Trendlines", True)
lines", True)
            if st.button("            if st.button("🔄 Refresh🔄 Refresh Chart"):
                st Chart"):
               .rerun()
 st.rerun()
        with col2:
                   with col2:
            ma = ma = orch.agents[' orch.agents['market_analystmarket_analyst']
            df = ma.fetch']
            df = ma.fetch_ohl_ohlcv(chcv(chart_pair, '1hart_pair, '1h', ', 24*chart_d24*chart_days)
ays)
            if            if df is df is not None:
                highs = df[' not None:
                highs = dfhigh'].['high'].values
                lows = df['lowvalues
                lows = df['low'].values'].values
               
                support_levels support_levels = []
                resistance_level = []
                resistance_levels =s = []
                for i in range(2 []
                for i in range(2, len(df)-, len(df)-2):
2):
                    if lows[i                    if lows[i] < lows[i] < lows[i-1] and lows[i]-1] and lows[i] < lows[i < lows[i+1]:
                        support+1]:
                       _levels.append support_levels.append((df['timestamp((df['timestamp'].iloc[i'].iloc[i], lows], lows[i]))
                    if[i]))
                    if highs[i highs[i] >] > highs[i-1] and highs[i-1] and highs[i highs[i] > highs[i] > highs[i+1]:
                        resistance_levels.append+1]:
                        resistance_level((dfs.append((df['timestamp'].iloc[i['timestamp'].iloc[i], highs], highs[i]))

[i]))

                fig                fig = go.Figure = go(data.Figure(data=[go.Candlestick(
                    x=df=[go.Candlestick(
                    x=df['timestamp'],
                    open=['timestamp'],
                    open=df['df['open'],
                    highopen'],
                    high=df['high'],
                   =df['high'],
                    low= low=df['low'],
df['low'],
                    close=df['close'],
                                       close=df['close'],
                    name='Price'
                ) name='Price'
                )])
                if show])
                if show_support:
                   _support:
                    for ts for ts, level in support_levels, level in support_levels[-10[-10:]:
                        fig.add_hline(y:]:
                        fig.add_hline(y=level, line_dash=level, line_dash="dot="dot", line_color="", line_color="green", opacity=0.green", opacity=0.3)
3)
                if                if show_trendlines show_trendlines:
                   :
                    if len(support_levels if len(support_levels) >= 2) >= 2:
                        x_vals = [support_levels[-2:
                        x_vals = [support_levels[-2][0], support_levels][0], support_levels[-1[-1][0][0]]
                        y_]]
                        y_vals = [supportvals = [support_levels[-2][1], support_levels[-2][1], support_levels[-1][1]]
                       _levels[-1][1]]
                        fig.add_trace(go fig.add_trace(go.Scatter(x=x_vals.Scatter(x=x, y=y_vals, mode='_vals, y=y_vals, mode='lines',lines', name=' name='UptUptrend', line=dict(colorrend', line=dict(color='='lime', dash='lime', dash='dashdash')))
')))
                    if len(resistance_level                    if len(resistance_levelss) >= ) >= 2:
                        x_2:
                        x_valsvals = [resistance_levels[- = [resistance_levels[-22][0], resistance][0], resistance_levels_levels[-1[-1][0][0]]
                        y_]]
                        y_vals = [resistance_levels[-2vals = [resistance_levels[-2][1], resistance_level][1], resistance_levels[-s[-1][1]]
                        fig1][1]]
                        fig.add_trace(.add_trace(go.Scgo.Scatter(x=x_atter(x=x_vals, y=y_vals, mode='lines', name='Downtrend', line=dict(color='red', dash='dash')))

vals, y=y_vals, mode='lines', name='Downtrend', line=dict(color='red', dash='dash')))

                               df['ema df['ema20'] = df['close'].ewm(20'] = df['close'].ewm(span=20).span=20).mean()
                dfmean()
                df['ema['ema50'] = df['close'].ew50'] = df['closem(span=50).'].ewm(span=50).mean()
                figmean()
                fig.add_trace(go.Scatter(x.add_trace(go.Scatter(x==df['timestampdf['timestamp'], y'], y=df['ema20'],=df['ema20'], name=' name='EMA20', line=dict(color='EMA20', line=dict(color='orange'orange')))
                fig.add)))
                fig.add_trace_trace(go.Scatter(x=(go.Scatter(x=df['timestamp'], y=df['timestamp'], y=df['df['ema50'], name='EMAema50'], name='EMA50', line=50', line=dict(color='blue')))

                fig.update_layoutdict(color='blue')))

                fig.update_layout(title=f"{chart(title=f"{chart_pair}_pair} – Last {chart_days – Last {chart_days} days} days", height=500)
               ", height=500)
                st.plotly_chart(fig, st.plotly_chart(fig, use_container_width=True use_container_width=True)

)

                st.subheader("                st.subheader("Ask about this chart")
               Ask about this chart")
                chart_query chart_query = st.text_input("Your = st.text_input("Your question about question about the chart:")
                if st.button(" the chart:")
                if st.button("Ask GeminiAsk Gemini about chart about chart"):
                    if chart"):
                    if chart_query and 'chat_query and' in st.session_state:
                        context 'chat' in st.session_state:
 = f"Current                        context = f"Current price: {df price: {df['close'].iloc[-['close'].iloc[-11]:.2f}.]:.2 "
                       f}. "
                        if if support_level support_levels:
                            context += f"s:
                            context += f"Recent support near {Recent support near {support_levelsupport_levels[-1][1]:s[-1][1]:..2f}. "
                        if resistance2f}. "
                        if resistance_levels:
                           _levels context +=:
                            context += f" f"Recent resistance near {resistance_levelsRecent resistance near {resistance_levels[-1][1[-1][1]:.2f]:.2f}. "
}. "
                        prompt = f                        prompt = f"Regarding the {"Regarding the {chart_pairchart_pair} chart} chart, {context} User asks, {context} User asks: {chart_query}"
                       : {chart_query}"
                        response = st.session response = st.session_state.chat.get_state.chat.get_response(prompt,_response(prompt, [], [])
                        [], [])
                        st.text_area(" st.text_area("GeminiGemini:", response, height:", response, height=150)
            else:
                st.error("=150)
            else:
                st.error("Failed toFailed to fetch data.")

    fetch data.")

    with tab6:
        st with tab6:
.subheader        st.subheader("Agent("Agent Team Chat")
        Team Chat")
        st.write st.write("Chat with all("Chat with all your agents collectively.")
 your agents collectively.")
        user_query = st.text_input("        user_query = st.text_input("Ask the agent team:", key="agent_chat_input")
Ask the agent team:", key="agent_chat_input")
        if        if st.button("Ask Agents"):
 st.button("Ask Agents"):
            if            if user_query user_query:
                market_ctx:
                market_ctx = "Market Analyst: " = "Market Analyst: " + ( + (str(orch.signstr(orch.signals[-als[-3:]) if3:]) if orch.signals else "No orch.signals else "No recent signals")
                recent signals")
                news_ctx = "News Sentiment: " + (str news_ctx = "News Sentiment: " + (str(orch.agents['(orch.agents['news_sentimentnews_sentiment'].analyze()) if'].analyze()) has if hasattr(orch.agents['attr(orch.agents['news_snews_sentimententiment'], 'analyze') else "Ne'], 'analyze') else "Neutral")
                prompt = f"""You are a team of trading agents: market analyst,utral")
                prompt = f"""You are a team of trading agents: market analyst, news analyst news analyst, technical strategist, technical strategist, risk manager,, risk manager, and execution and execution optimizer.
A user optimizer.
A user asks: asks: {user_query}
 {user_query}
Provide a collaborative answerProvide a collaborative answer incorporating insights from each agent. incorporating insights from each agent. Be concise Be concise and helpful and helpful.
Current context:.
Current context: {market {market_ctx} |_ctx} | {news_ctx}
"""
                if {news_ctx}
"""
 'chat' in                if 'chat' in st.session_state st.session_state:
:
                    response = st.session_state.chat                    response = st.session_state.chat.get_response(prompt, [],.get_response(prompt, [], [])
                    st [])
                    st.text.text_area("Agent_area("Agent Team:", response, height= Team:", response, height=300)
300)
                else                else:
                   :
                    st.error("Chat not initialized st.error("Chat not initialized.")

if __name.")

if __name__ ==__ == "__main__":
    "__main main()
