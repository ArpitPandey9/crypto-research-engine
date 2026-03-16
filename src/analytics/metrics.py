import pandas as pd
import numpy as np


def total_return(equity: pd.Series) -> float:
    """
    Total return from an equity curve.

    If equity starts at 1 and ends at 1.25,
    total return = 1.25 - 1 = 0.25 = 25%.
    """
    return equity.iloc[-1] - 1

def annualized_return(equity: pd.Series) -> float:
    """
    Annualized return from an equity curve.

    We use:
    (final equity) ** (252 / number of periods) - 1

    This converts the total growth into an approximate yearly return.
    """
    n = len(equity)
    final_value = equity.iloc[-1]
    return (final_value ** (252 / n)) - 1

def annualized_volatility(returns: pd.Series) -> float:
    """
    Annualized volatility from daily returns.

    We use:
    std(daily returns) * sqrt(252)

    This shows how unstable or risky the return path is on a yearly basis.
    """
    return returns.std() * np.sqrt(252)

def sharpe_ratio(returns: pd.Series) -> float:
    """
    Sharpe ratio using daily returns and no risk-free rate.

    Formula:
    mean(daily returns) / std(daily returns) * sqrt(252)
    """
    if returns.std() == 0:
        return np.nan

    return (returns.mean() / returns.std()) * np.sqrt(252)

def max_drawdown(equity: pd.Series) -> float:
    """
    Maximum drawdown from an equity curve.

    Steps:
    1. Find the running peak of the equity curve
    2. Compare current equity to that peak
    3. Measure the worst drop
    """
    running_max = equity.cummax()
    drawdown = (equity / running_max) - 1
    return drawdown.min()

def exposure(position: pd.Series) -> float:
    """
    Exposure = average time spent in the market.

    If position is 1 half the time and 0 half the time,
    exposure = 0.5 = 50%.
    """
    return position.mean()

def trade_count(position: pd.Series) -> int:
    """
    Approximate number of position changes.

    We count how many times the position changes
    from 0 to 1 or from 1 to 0.
    """
    return int(position.diff().fillna(0).ne(0).sum())