import backtrader as bt


def log_results(data_name: str, results) -> None:
    print("\n\n" + 20 * "=" + f" {data_name} " + 20 * "=")
    strat = results[0]
    sharpe_ratio = strat.analyzers.sharperatio.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    trade_analysis = strat.analyzers.tradeanalyzer.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    print(f'Sharpe Ratio: {sharpe_ratio["sharperatio"]}')
    print(f'Max Drawdown: {drawdown["max"]["drawdown"]}')
    print(f"Number of Trades: {trade_analysis.total.closed}")
    print(f"Winning Trades: {trade_analysis.won.total}")
    print(f"Losing Trades: {trade_analysis.lost.total}")
    print(f'Average Trade Return: {returns["rnorm"]}')
    print(f'Total Returns: {returns["rtot"]}')
    print(f"Final Balance: {strat.broker.getvalue()}")


def test_strategy(
    strategy: bt.Strategy,
    data_feed: bt.FeedBase,
    strategy_params: dict = None,
    cerebro_params: dict = None,
):
    cerebro = bt.Cerebro()
    # Add the Strategy
    cerebro.addstrategy(strategy, **strategy_params)
    # Add trade size manager (Percent of equity)
    if cerebro_params is not None and "percents" in cerebro_params.keys():
        cerebro.addsizer(bt.sizers.PercentSizer, percents=cerebro_params["percents"])
    else:
        cerebro.addsizer(bt.sizers.FixedSize)

    cerebro.adddata(data_feed)  # Add DataFeed

    # Set cash and commission
    if cerebro_params is not None and "initial_cash" in cerebro_params.keys():
        cerebro.broker.setcash(cerebro_params["initial_cash"])
    else:
        cerebro.broker.setcash(100_000.0)
    cerebro.broker.setcommission(commission=0.001)

    # Add Analyzers for final review
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, riskfreerate=0.01)
    cerebro.addanalyzer(bt.analyzers.DrawDown)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer)
    cerebro.addanalyzer(bt.analyzers.Returns)

    results = cerebro.run(stdstats=False)

    return results, cerebro
