from datetime import datetime
from math import exp
from typing import Dict

from pandas import DataFrame

from freqtrade.optimize.hyperopt import IHyperOptLoss


# Define some constants:

# set TARGET_TRADES to suit your number concurrent trades so its realistic
# to the number of days
TARGET_TRADES = 600
# This is assumed to be expected avg profit * expected trade count.
# For example, for 0.35% avg per trade (or 0.0035 as ratio) and 1100 trades,
# self.expected_max_profit = 3.85
# Check that the reported Σ% values do not exceed this!
# Note, this is ratio. 3.85 stated above means 385Σ%.
EXPECTED_MAX_PROFIT = 3.0

# max average trade duration in minutes
# if eval ends with higher value, we consider it a failed eval
MAX_ACCEPTED_TRADE_DURATION = 300


class FSampleStrategy(IHyperOptLoss):
    """
    Defines the default loss function for hyperopt
    This is intended to give you some inspiration for your own loss function.

    The Function needs to return a number (float) - which becomes smaller for better backtest
    results.
    """

    @staticmethod
    def hyperopt_loss_function(results: DataFrame, trade_count: int,
                               min_date: datetime, max_date: datetime,
                               config: Dict, processed: Dict[str, DataFrame],
                               *args, **kwargs) -> float:
        """
        Objective function, returns smaller number for better results
        """

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe["adx"] = ta.ADX(dataframe)
        # RSI
        dataframe["rsi"] = ta.RSI(dataframe)

        # Stochastic Fast
        stoch_fast = ta.STOCHF(dataframe)
        dataframe["fastd"] = stoch_fast["fastd"]
        dataframe["fastk"] = stoch_fast["fastk"]

        # MACD
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        # MFI
        dataframe["mfi"] = ta.MFI(dataframe)

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=2
        )
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        dataframe["bb_percent"] = (dataframe["close"] - dataframe["bb_lowerband"]) / (
            dataframe["bb_upperband"] - dataframe["bb_lowerband"]
        )
        dataframe["bb_width"] = (
            dataframe["bb_upperband"] - dataframe["bb_lowerband"]
        ) / dataframe["bb_middleband"]

        # Parabolic SAR
        dataframe["sar"] = ta.SAR(dataframe)

        # TEMA - Triple Exponential Moving Average
        dataframe["tema"] = ta.TEMA(dataframe, timeperiod=9)

        # Cycle Indicator
        # ------------------------------------
        # Hilbert Transform Indicator - SineWave
        hilbert = ta.HT_SINE(dataframe)
        dataframe["htsine"] = hilbert["sine"]
        dataframe["htleadsine"] = hilbert["leadsine"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe.loc[
            (
                # Signal: RSI crosses above 30
                (qtpylib.crossed_above(dataframe["rsi"], 30))
                & (dataframe["tema"] <= dataframe["bb_middleband"])
                & (  # Guard: tema below BB middle
                    dataframe["tema"] > dataframe["tema"].shift(1)
                )
                & (  # Guard: tema is raising
                    dataframe["volume"] > 0
                )  # Make sure Volume is not 0
            ),
            "enter_long",
        ] = 1

        dataframe.loc[
            (
                # Signal: RSI crosses above 70
                (qtpylib.crossed_above(dataframe["rsi"], 70))
                & (dataframe["tema"] > dataframe["bb_middleband"])
                & (  # Guard: tema above BB middle
                    dataframe["tema"] < dataframe["tema"].shift(1)
                )
                & (  # Guard: tema is falling
                    dataframe["volume"] > 0
                )  # Make sure Volume is not 0
            ),
            "enter_short",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # Signal: RSI crosses above 70
                (qtpylib.crossed_above(dataframe["rsi"], 70))
                & (dataframe["tema"] > dataframe["bb_middleband"])
                & (  # Guard: tema above BB middle
                    dataframe["tema"] < dataframe["tema"].shift(1)
                )
                & (  # Guard: tema is falling
                    dataframe["volume"] > 0
                )  # Make sure Volume is not 0
            ),
            "exit_long",
        ] = 1

        dataframe.loc[
            (
                # Signal: RSI crosses above 30
                (qtpylib.crossed_above(dataframe["rsi"], 30))
                &
                # Guard: tema below BB middle
                (dataframe["tema"] <= dataframe["bb_middleband"])
                & (dataframe["tema"] > dataframe["tema"].shift(1))
                & (  # Guard: tema is raising
                    dataframe["volume"] > 0
                )  # Make sure Volume is not 0
            ),
            "exit_short",
        ] = 1

        return dataframe

        trade_loss = 1 - 0.25 * exp(-(trade_count - TARGET_TRADES) ** 2 / 10 ** 5.8)
        profit_loss = max(0, 1 - total_profit / EXPECTED_MAX_PROFIT)
        duration_loss = 0.4 * min(trade_duration / MAX_ACCEPTED_TRADE_DURATION, 1)
        result = trade_loss + profit_loss + duration_loss
        return result
