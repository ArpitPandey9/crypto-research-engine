from pathlib import Path
import pandas as pd

# Find project root so paths work on any computer
ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"


def main() -> None:
    """
    Reads wide price data (BTC + ETH), computes:
    1) daily returns
    2) cumulative $1 growth
    and saves both as CSV files.
    """
    # 1) Load wide prices file (date index, columns=coins)
    prices_path = PROCESSED / "prices_btc_eth_wide_processed.csv"
    prices = pd.read_csv(prices_path, index_col=0, parse_dates=True)

    # 2) Compute daily returns: (today/yesterday) - 1
    returns = prices.pct_change().dropna()

    # 3) Save returns
    returns_path = PROCESSED / "returns_btc_eth_wide.csv"
    returns.to_csv(returns_path)

    # 4) Compute cumulative growth of $1: multiply (1 + returns) over time
    cum = (1 + returns).cumprod()

    # 5) Save cumulative returns
    cum_path = PROCESSED / "cum_returns_btc_eth.csv"
    cum.to_csv(cum_path)

    # 6) Print small preview for sanity check
    print("Saved:", returns_path)
    print("Saved:", cum_path)
    print("\nReturns preview:\n", returns.head())


if __name__ == "__main__":
    main()