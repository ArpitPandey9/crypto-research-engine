import streamlit as st
import pandas as pd
from pathlib import Path

from src.strategies.ma_crossover import generate_signals, backtest
from src.analytics.metrics import total_return, annualized_volatility, max_drawdown

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "processed" / "prices_btc_eth_wide_processed.csv"

st.title("Crypto Research Engine")
st.subheader("Interactive Strategy Lab")
st.write(
    "This dashboard allows a user to explore the BTC moving-average crossover strategy."
)

fast_window = st.slider("Fast SMA Window", min_value=5, max_value=50, value=20)
slow_window = st.slider("Slow SMA Window", min_value=20, max_value=200, value=50)

cost_per_trade = st.number_input(
    "Transaction Cost (decimal form)",
    min_value=0.0,
    max_value=0.01,
    value=0.001,
    step=0.0001,
    format="%.4f",
)

if fast_window >= slow_window:
    st.warning("Fast SMA must be smaller than Slow SMA. Please adjust the sliders.")
    st.stop()

prices = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True)
btc = prices["bitcoin"].copy()

signals = generate_signals(btc, fast=fast_window, slow=slow_window)
results = backtest(signals, cost_per_trade=cost_per_trade)

st.subheader("Selected Parameters")
st.write(
    f"Fast SMA = {fast_window}, Slow SMA = {slow_window}, Transaction Cost = {cost_per_trade:.4f}"
)

st.subheader("Equity Curve Comparison")
st.write(
    "This chart compares Buy & Hold with the strategy before costs (Gross) "
    "and after costs (Net). The gap between Gross and Net shows the impact of trading costs."
)

# Better chart labels for non-technical users
chart_df = results[
    ["equity_asset", "equity_strategy_gross", "equity_strategy_net"]
].rename(
    columns={
        "equity_asset": "Buy & Hold",
        "equity_strategy_gross": "Strategy Gross",
        "equity_strategy_net": "Strategy Net",
    }
)

st.line_chart(chart_df)

col1, col2, col3 = st.columns(3)

col1.metric("Buy & Hold Final Equity", f"{results['equity_asset'].iloc[-1]:.4f}")
col2.metric(
    "Strategy Gross Final Equity",
    f"{results['equity_strategy_gross'].iloc[-1]:.4f}",
)
col3.metric(
    "Strategy Net Final Equity",
    f"{results['equity_strategy_net'].iloc[-1]:.4f}",
)

st.subheader("Strategy Net Risk/Return Summary")

m1, m2, m3 = st.columns(3)

net_total_return = total_return(results["equity_strategy_net"])
net_volatility = annualized_volatility(results["net_strategy_return"])
net_drawdown = max_drawdown(results["equity_strategy_net"])

m1.metric("Net Total Return", f"{net_total_return:.4f}")
m2.metric("Net Annualized Volatility", f"{net_volatility:.4f}")
m3.metric("Net Max Drawdown", f"{net_drawdown:.4f}")

# Small interpretation line
buy_hold_final = results["equity_asset"].iloc[-1]
net_final = results["equity_strategy_net"].iloc[-1]

if net_final > buy_hold_final:
    st.success(
        "Under the selected parameters, the net strategy finishes above Buy & Hold."
    )
else:
    st.info(
        "Under the selected parameters, the net strategy finishes below Buy & Hold."
    )

st.subheader("What this dashboard shows")
st.write(
    "This app lets a user explore a BTC moving-average crossover strategy by changing "
    "the fast SMA, slow SMA, and transaction cost. "
    "The chart compares Buy & Hold, Strategy Gross (before costs), and Strategy Net (after costs). "
    "This helps show how parameter choices and trading costs affect performance."
)

st.subheader("Backtest Preview")

preview_cols = [
    "price",
    "signal",
    "position",
    "gross_strategy_return",
    "net_strategy_return",
]

# Rounded display for cleaner tables
preview_df = results[preview_cols].copy()
preview_df["price"] = preview_df["price"].round(2)
preview_df["gross_strategy_return"] = preview_df["gross_strategy_return"].round(4)
preview_df["net_strategy_return"] = preview_df["net_strategy_return"].round(4)

st.write("Last 5 rows of the backtest:")
st.dataframe(preview_df.tail())

st.write("Example rows where the strategy was in the market:")
active_rows = preview_df[preview_df["position"] == 1].head(5)
st.dataframe(active_rows)