import pandas as pd
import matplotlib.pyplot as plt

# 1) Load cumulative returns CSV
cum = pd.read_csv(
    "data/processed/cum_returns_btc_eth.csv",
    index_col=0,        # first column is the date index
    parse_dates=True    # convert index to datetime
)

# 2) Plot each asset as a separate chart
for asset in cum.columns:
    plt.figure()
    plt.plot(cum.index, cum[asset])
    plt.title(f"Cumulative $1 Growth: {asset}")
    plt.xlabel("date")
    plt.ylabel("growth")
    plt.tight_layout()
    plt.show()