import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

df = pd.read_csv("data/processed/results_ma_btc.csv", index_col=0, parse_dates=True)

plt.figure()
plt.plot(df.index, df["equity_asset"], label="Buy & Hold")
plt.plot(df.index, df["equity_strategy"], label="MA Strategy")
plt.title("BTC Equity Curves")
plt.xlabel("date")
plt.ylabel("growth of $1")
plt.legend()
plt.tight_layout()

# Save chart
figures_dir = Path("reports/figures")
figures_dir.mkdir(parents=True, exist_ok=True)
plt.savefig(figures_dir / "btc_equity_curves.png", dpi=150)

plt.show()