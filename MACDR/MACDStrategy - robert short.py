# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy
from freqtrade.strategy import CategoricalParameter, DecimalParameter, IntParameter
from pandas import DataFrame
# --------------------------------

from freqtrade.strategy.interface import IStrategy
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
import talib.abstract as ta


class MACDRS(IStrategy):
    """
    """
    INTERFACE_VERSION: int = 3

    # Can this strategy go short?
    can_short: bool = True

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {
        "0": 0.03024,
        "296": 0.02924,
        "596": 0.02545,
        "840": 0.02444,
        "966": 0.02096,
        "1258": 0.01709,
        "1411": 0.01598,
        "1702": 0.0122,
        "1893": 0.00732,
        "2053": 0.00493,
        "2113": 0
    }

    # Optimal stoploss designed for the strategy
    # This attribute will be overridden if the config file contains "stoploss"
    stoploss = -0.04032

    # Optimal timeframe for the strategy
    timeframe = '5m'

    # Buy hyperspace params:
    
    ema200_long = IntParameter(15, 300, default=200, space='buy', optimize=True)
    ema200_short = IntParameter(15, 300, default=200, space='buy', optimize=True)

    buy_params = {
        "ema200_long": 200,
        "ema200_short": 200,
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        for val in self.ema200_long.range:
            dataframe[f'ema200_long_{val}'] = ta.EMA(dataframe, timeperiod=val)

        for val in self.ema200_short.range:
            dataframe[f'ema200_short_{val}'] = ta.EMA(dataframe, timeperiod=val)

        #RSI
        dataframe['rsi'] = ta.RSI(dataframe)
 
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        """
        dataframe.loc[
            (
                    (dataframe['rsi'].rolling(8).min() < 41) &
                    (dataframe['close'] > dataframe[f'ema200_long_{self.ema200_long.value}']) &
                    (qtpylib.crossed_above(dataframe['macd'], dataframe['macdsignal']))
            ),
            'enter_long'] = 0

        dataframe.loc[
            (
                    (dataframe['rsi'].rolling(8).min() > 41) &
                    (dataframe['close'] < dataframe[f'ema200_short_{self.ema200_short.value}']) &
                    (qtpylib.crossed_below(dataframe['macd'], dataframe['macdsignal']))
            ),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        """

        dataframe.loc[
            (
                    (dataframe['rsi'].rolling(8).max() > 93) &
                    (dataframe['macd'] > 0) &
                    (qtpylib.crossed_below(dataframe['macd'], dataframe['macdsignal']))
            ),
            'exit_long'] = 0
            
        dataframe.loc[
            (
                    (dataframe['rsi'].rolling(8).max() < 93) &
                    (dataframe['macd'] < 0) &
                    (qtpylib.crossed_above(dataframe['macd'], dataframe['macdsignal']))
            ),
            'exit_short'] = 1

        return dataframe
