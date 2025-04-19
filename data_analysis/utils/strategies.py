import backtrader as bt
import numpy as np

from backtrader.studies.contrib.fractal import Fractal
from .indicators import VWAPRollingIndicator


class TriplleMARSIFracStrategy(bt.Strategy):
    params = (
        # Position Management Params
        ("atr_period", 9),  # ATR Period
        ("atr_multiplier", 1.5),  # ATR multiplier for SL calculation
        ("rrr", 2),  # Risk-Reward Ratio
        # Triple MA Params
        ("fastMA_period", 21),
        ("midMA_period", 50),
        ("slowMA_period", 200),
        # RSI params
        ("rsi_period", 14),
    )

    def __init__(self):
        # initialize the EMA indicator on data feed
        self.fast_ma = bt.ind.SmoothedMovingAverage(period=self.params.fastMA_period)
        self.mid_ma = bt.ind.SmoothedMovingAverage(period=self.params.midMA_period)
        self.slow_ma = bt.ind.SmoothedMovingAverage(period=self.params.slowMA_period)
        self.rsi = bt.ind.RelativeStrengthIndex(period=self.params.rsi_period)
        self.fractal = Fractal()
        self.atr = bt.indicators.AverageTrueRange(period=self.params.atr_period)
        self.order = None

    def _isBulluish(self, idx: int):
        if len(self.data) < idx + 1:
            self.log("[Error]: Index out of bounds for `isBullish`")
            return
        return self.data.close[idx] > self.data.open[idx]

    def _isEngulfing(self, idx: int):
        if len(self.data) < idx + 1:
            self.log("[Error]: Index out of bounds for `isEnglufing`")
            return
        return (
            self.data.open[idx + 1] < self.data.close[idx]
            if self._isBulluish(idx)
            else self.data.open[idx + 1] > self.data.close[idx]
        )

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, {order.executed.price:.2f}")
            elif order.issell():
                self.log(f"SELL EXECUTED, {order.executed.price:.2f}")
        self.order = None

    def log(self, txt):
        dt = self.data.datetime.date(0)
        print(f"{dt.isoformat()} {txt}")

    def _sell(self):
        price = self.data.close[0]
        sl_price = price + self.atr * self.params.atr_multiplier
        tp_price = price - np.abs(sl_price - price) * self.params.rrr
        if tp_price > price or tp_price < 0:
            self.log(
                f"Take profit price {tp_price:.2f} is greater than entry price {price:.2f}, not placing order."
            )
            return
        if sl_price < price or sl_price < 0:
            self.log(
                f"Stop loss price {sl_price:.2f} is less than entry price {price:.2f}, not placing order."
            )
            return
        self.order = self.sell_bracket(
            exectype=bt.Order.Market,
            price=price,
            stopprice=sl_price,
            limitprice=tp_price,
            stopargs=dict(exectype=bt.Order.Stop),
            limitargs=dict(exectype=bt.Order.Limit),
        )
        self.log(
            f"Bracket order placed: Entry {price:.2f}, SL {sl_price:.2f}, TP {tp_price:.2f}"
        )

    def _buy(self):
        price = self.data.close[0]
        sl_price = price - self.atr * self.params.atr_multiplier
        tp_price = price + np.abs(sl_price - price) * self.params.rrr
        if tp_price < price or tp_price < 0:
            self.log(
                f"Take profit price {tp_price:.2f} is less than entry price {price:.2f}, not placing order."
            )
            return
        if sl_price > price or sl_price < 0:
            self.log(
                f"Stop loss price {sl_price:.2f} is greater than entry price {price:.2f}, not placing order."
            )
            return

        self.order = self.buy_bracket(
            exectype=bt.Order.Market,
            price=price,
            stopprice=sl_price,
            limitprice=tp_price,
            stopargs=dict(exectype=bt.Order.Stop),
            limitargs=dict(exectype=bt.Order.Limit),
        )
        self.log(
            f"Bracket order placed: Entry {price:.2f}, SL {sl_price:.2f}, TP {tp_price:.2f}"
        )

    def next(self):
        # if in market position, do nothing, return
        if self.position:
            return

        last_high = self.data.high[0]
        last_low = self.data.low[0]
        if (
            self.fractal.fractal_bearish[0] != 0
            and self.rsi[0] < 50
            and last_high < self.fast_ma[0]
            and self.fast_ma[0] < self.mid_ma[0]
            # self.mid_ma[0] < self.slow_ma[0]
        ):
            self._sell()

        elif (
            self.fractal.fractal_bullish[0] != 0
            and self.rsi[0] > 50
            and last_low > self.fast_ma[0]
            and self.fast_ma[0] > self.mid_ma[0]
            # self.mid_ma[0] > self.slow_ma[0]
        ):
            self._buy()


class EMASwing(bt.Strategy):
    params = (
        ("ema_period", 50),  # EMA Period
        ("atr_period", 9),  # ATR Period
        ("atr_multiplier", 1.5),  # ATR multiplier for SL calculation
        ("pivot_window", 5),  # 5 bars for pivot high/low
        ("rrr", 2),  # Risk-Reward Ratio
    )

    def __init__(self):
        # initialize the EMA indicator on data feed
        # self.ema = bt.talib.EMA(self.data.close, self.params.ema_period)
        self.ema = bt.indicators.ExponentialMovingAverage(period=self.params.ema_period)
        self.atr = bt.indicators.AverageTrueRange(period=self.params.atr_period)
        self.crossover = bt.indicators.CrossOver(self.data.close, self.ema)
        self.order = None
        self.prev_pivot_high = self.data.low[0]
        self.prev_pivot_low = self.data.high[0]

    def _isBulluish(self, idx: int):
        if len(self.data) < idx + 1:
            self.log("[Error]: Index out of bounds for `isBullish`")
            return
        return self.data.close[idx] > self.data.open[idx]

    def _isEngulfing(self, idx: int):
        if len(self.data) < idx + 1:
            self.log("[Error]: Index out of bounds for `isEnglufing`")
            return
        return (
            self.data.open[idx + 1] < self.data.close[idx]
            if self._isBulluish(idx)
            else self.data.open[idx + 1] > self.data.close[idx]
        )

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, {order.executed.price:.2f}")
            elif order.issell():
                self.log(f"SELL EXECUTED, {order.executed.price:.2f}")
        self.order = None

    def log(self, txt):
        dt = self.data.datetime.date(0)
        print(f"{dt.isoformat()} {txt}")

    def _update_pivots(self):
        if (
            np.max(self.data.high.get(size=self.params.pivot_window * 2 + 1))
            == self.data.high[self.params.pivot_window]
        ):
            self.prev_pivot_high = self.data.high[self.params.pivot_window]
        if (
            np.min(self.data.low.get(size=self.params.pivot_window * 2 + 1))
            == self.data.low[self.params.pivot_window]
        ):
            self.prev_pivot_low = self.data.low[self.params.pivot_window]

    def next(self):
        # if not in a market position, check for crossover from below
        if self.position:
            return
        if self.crossover[0] > 0 and (self._isEngulfing(0) or self._isEngulfing(1)):
            price = self.data.close[0]
            sl_price = price - self.atr * self.params.atr_multiplier
            tp_price = price + np.abs(sl_price - price) * self.params.rrr
            if tp_price < price or tp_price < 0:
                self.log(
                    f"Take profit price {tp_price:.2f} is less than entry price {price:.2f}, not placing order."
                )
                return
            if sl_price > price or sl_price < 0:
                self.log(
                    f"Stop loss price {sl_price:.2f} is greater than entry price {price:.2f}, not placing order."
                )
                return

            self.order = self.buy_bracket(
                exectype=bt.Order.Market,
                price=price,
                stopprice=sl_price,
                limitprice=tp_price,
                stopargs=dict(exectype=bt.Order.Stop),
                limitargs=dict(exectype=bt.Order.Limit),
            )
            self.log(
                f"Bracket order placed: Entry {price:.2f}, SL {sl_price:.2f}, TP {tp_price:.2f}"
            )

        # if in a position, check for crossover from above for exit
        elif self.crossover[0] < 0 and (self._isEngulfing(0) or self._isEngulfing(1)):
            price = self.data.close[0]
            sl_price = price + self.atr * self.params.atr_multiplier
            tp_price = price - np.abs(sl_price - price) * self.params.rrr
            if tp_price > price or tp_price < 0:
                self.log(
                    f"Take profit price {tp_price:.2f} is greater than entry price {price:.2f}, not placing order."
                )
                return
            if sl_price < price or sl_price < 0:
                self.log(
                    f"Stop loss price {sl_price:.2f} is less than entry price {price:.2f}, not placing order."
                )
                return
            self.order = self.sell_bracket(
                exectype=bt.Order.Market,
                price=price,
                stopprice=sl_price,
                limitprice=tp_price,
                stopargs=dict(exectype=bt.Order.Stop),
                limitargs=dict(exectype=bt.Order.Limit),
            )
            self.log(
                f"Bracket order placed: Entry {price:.2f}, SL {sl_price:.2f}, TP {tp_price:.2f}"
            )


class LongStraddleSimplified(bt.Strategy):
    params = (
        ("atr_period", 14),
        ("atr_multiplier", 1.0),
        ("atr_sma_period", 20),
        ("sma_period", 20),
        ("rrr", 2.0),  # TP is 2x the risk distance
    )

    def __init__(self):
        self.atr = bt.indicators.ATR(period=self.params.atr_period)
        self.atr_sma = bt.indicators.SMA(self.atr, period=self.params.atr_sma_period)
        self.close_sma = bt.indicators.SMA(
            self.datas[0].close, period=self.params.sma_period
        )

        # To prevent placing multiple orders while one is pending
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        if order.status in [order.Completed]:
            if order.isbuy():
                print(
                    f"{self.datas[0].datetime.date(0)} BUY EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}, "
                    f"Size: {order.executed.size}"
                )

            elif order.issell():
                print(
                    f"{self.datas[0].datetime.date(0)} SELL EXECUTED, Price: {order.executed.price:.2f}, "
                    f"Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}, "
                    f"Size: {order.executed.size}"
                )

            self.bar_executed = len(self)  # Bar number when order was executed

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f"{self.datas[0].datetime.date(0)} Order Canceled/Margin/Rejected")

        # Reset order status tracking
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        print(
            f"{self.datas[0].datetime.date(0)} TRADE PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}"
        )

    def next(self):
        # Wait for indicators to have enough data
        # Use max period from all indicators used in the condition + 1
        if len(self) <= max(self.params.atr_period, 20) + 1:
            return

        # Check if an order is pending. If so, do not send another one
        # if self.order:
        #     return

        # Check if we are already in the market
        if self.position:
            return

        # Calculate current indicator values
        atr_value = self.atr[0]
        atr_sma_value = self.atr_sma[0]
        close_value = self.datas[0].close[0]
        close_sma_value = self.close_sma[0]

        # Define entry condition
        high_volatility_condition = (
            close_value > close_sma_value and atr_value > atr_sma_value
        )

        if high_volatility_condition:
            # Calculate Stop Loss Price based on current close (potential entry)
            potential_entry = close_value
            # stop_loss_price = potential_entry * (1.0 - self.params.stop_loss_percent / 100.0)
            # take_profit_price = potential_entry * (1.0 + self.take_profit_percent / 100.0)
            sl_diff = atr_value * self.params.atr_multiplier
            stop_loss_price = potential_entry - sl_diff
            take_profit_price = potential_entry + self.params.rrr * sl_diff
            print(f"{self.datas[0].datetime.date(0)} --- ENTRY SIGNAL ---")
            print(f"Potential Entry: {potential_entry:.2f}")
            print(f"Stop Loss Price: {stop_loss_price:.2f}")
            print(f"Take Profit Price: {take_profit_price:.2f}")

            # Place Buy order with attached Stop Loss and Take Profit (Bracket Order)
            self.order = self.buy_bracket(
                exectype=bt.Order.Market,
                transmit=True,  # Transmit the main order immediately
                # The following create virtual child orders managed by backtrader
                stopprice=stop_loss_price,
                stopexec=bt.Order.Stop,  # Stop Market order for SL
                limitprice=take_profit_price,
                limitexec=bt.Order.Limit,  # Limit order for TP
            )
            # The old way using parent/transmit=False is more complex
            # self.mainside = self.buy(size=size, exectype=bt.Order.Market)
            # self.sell(exectype=bt.Order.Stop, price=stop_loss_price, size=size, parent=self.mainside)
            # self.sell(exectype=bt.Order.Limit, price=take_profit_price, size=size, parent=self.mainside)


class VWAPStrategy(bt.Strategy):
    params = (
        ("atr_period", 9),
        ("atr_multiplier", 1.0),
        ("rrr", 2),  # Risk-Reward Ratio
    )

    def __init__(self):
        # initialize the VWAP indicator on data feed
        self.vwap = VWAPRollingIndicator(self.data)
        self.crossover = bt.indicators.CrossOver(self.data.close, self.vwap)
        self.order = None

        self.atr = bt.ind.AverageTrueRange(period=self.p.atr_period)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f"BUY EXECUTED, {order.executed.price:.2f}")
            elif order.issell():
                self.log(f"SELL EXECUTED, {order.executed.price:.2f}")
        self.order = None

    def log(self, txt):
        dt = self.data.datetime.date(0)
        print(f"{dt.isoformat()} {txt}")

    def next(self):
        # if not in a market position, check for crossover from below
        if self.position:
            return
        if self.crossover > 0 and self.data.close[1] > self.data.open[1]:
            price = self.data.close[0]
            sl_diff = self.atr[0] * self.p.atr_multiplier
            sl_price = price - sl_diff
            tp_price = price + sl_diff * self.params.rrr

            self.order = self.buy_bracket(
                exectype=bt.Order.Market,
                price=price,
                stopprice=sl_price,
                limitprice=tp_price,
                stopargs=dict(exectype=bt.Order.Stop),
                limitargs=dict(exectype=bt.Order.Limit),
            )
            self.log(
                f"Bracket order placed: Entry {price:.2f}, SL {sl_price:.2f}, TP {tp_price:.2f}"
            )

        # if in a position, check for crossover from above for exit
        elif self.crossover < 0 and self.data.close[1] < self.data.open[1]:
            price = self.data.close[0]
            sl_diff = self.atr[0] * self.p.atr_multiplier
            sl_price = price + sl_diff
            tp_price = price - sl_diff * self.params.rrr

            self.order = self.sell_bracket(
                exectype=bt.Order.Market,
                # size=size,
                price=price,
                stopprice=sl_price,
                limitprice=tp_price,
                stopargs=dict(exectype=bt.Order.Stop),
                limitargs=dict(exectype=bt.Order.Limit),
            )
            self.log(
                f"Bracket order placed: Entry {price:.2f}, SL {sl_price:.2f}, TP {tp_price:.2f}"
            )
