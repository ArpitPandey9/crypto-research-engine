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


def backtest(df: pd.DataFrame) -> pd.DataFrame:
    """
    Backtest the MA crossover strategy.

    What we add:
    - asset_return: normal BTC daily return
    - position: actual market exposure based on yesterday's signal
    - strategy_return: return earned by the strategy
    - equity curves: growth of $1 for asset and strategy
    """
    out = df.copy()

    # Daily BTC return
    out["asset_return"] = out["price"].pct_change()

    # Use yesterday's signal as today's position to avoid lookahead bias
    out["position"] = out["signal"].shift(1).fillna(0)

    # Strategy earns return only when position = 1
    out["strategy_return"] = out["position"] * out["asset_return"]

    # Equity curves (growth of $1)
    out["equity_asset"] = (1 + out["asset_return"]).cumprod()
    out["equity_strategy"] = (1 + out["strategy_return"]).cumprod()

    return out.dropna()