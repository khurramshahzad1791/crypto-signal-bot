# SimpleStrategy.py
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class SimpleStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = '5m'
    can_short = True

    minimal_roi = {
        "0": 0.01
    }

    stoploss = -0.02

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] < 30)
            ),
            'enter_long'] = 1

        dataframe.loc[
            (
                (dataframe['rsi'] > 70)
            ),
            'enter_short'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > 70)
            ),
            'exit_long'] = 1

        dataframe.loc[
            (
                (dataframe['rsi'] < 30)
            ),
            'exit_short'] = 1
        return dataframe
