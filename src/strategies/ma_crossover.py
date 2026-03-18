import pandas as pd

def sma(series: pd.Series, window: int) -> pd.Series:
    """
    SMA = Simple Moving Average

    What it does:
    It takes the average of the last N prices.
    Example:
    If window = 3, it looks at the last 3 prices and finds their average.

    Why we use it:
    It smooths noisy price data and helps us see trend direction more clearly.
    """
    return series.rolling(window=window).mean()


def generate_signals(price: pd.Series, fast: int = 20, slow: int = 50) -> pd.DataFrame:
    """
    Create moving-average crossover signals.

    Signal rule:
    - if fast SMA > slow SMA, signal = 1
    - otherwise, signal = 0
    """
    if fast >= slow:
        raise ValueError("fast must be smaller than slow")

    fast_ma = sma(price, fast)
    slow_ma = sma(price, slow)

    signal = (fast_ma > slow_ma).astype(int)

    df = pd.DataFrame({
        "price": price,
        "fast_ma": fast_ma,
        "slow_ma": slow_ma,
        "signal": signal
    })

    return df.dropna()


def backtest(df: pd.DataFrame, cost_per_trade: float = 0.001) -> pd.DataFrame:
    """
    Backtest the MA crossover strategy with transaction costs.

    What we add:
    - asset_return: BTC daily return
    - position: actual market exposure based on yesterday's signal
    - gross_strategy_return: return before costs
    - trade_flag: shows when position changed
    - transaction_cost: fixed cost when position changes
    - net_strategy_return: return after costs
    - equity curves for asset, gross strategy, and net strategy
    """
    out = df.copy()

    # 1) Daily BTC return
    out["asset_return"] = out["price"].pct_change()

    # 2) Use yesterday's signal as today's position
    out["position"] = out["signal"].shift(1).fillna(0)

    # 3) Gross strategy return = before costs
    out["gross_strategy_return"] = out["position"] * out["asset_return"]

    # 4) trade_flag becomes 1 when position changes
    out["trade_flag"] = out["position"].diff().fillna(0).ne(0).astype(int)

    # 5) Apply transaction cost only when trade happens
    out["transaction_cost"] = out["trade_flag"] * cost_per_trade

    # 6) Net strategy return = after costs
    out["net_strategy_return"] = out["gross_strategy_return"] - out["transaction_cost"]

    # 7) Equity curves
    out["equity_asset"] = (1 + out["asset_return"]).cumprod()
    out["equity_strategy_gross"] = (1 + out["gross_strategy_return"]).cumprod()
    out["equity_strategy_net"] = (1 + out["net_strategy_return"]).cumprod()

    return out.dropna()