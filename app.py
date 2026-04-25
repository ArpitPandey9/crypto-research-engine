# app.py

"""
Module: Whale Flow Research Dashboard (V4)
Description:
- Streamlit interface for the whale-flow research engine
- Loads enriched whale events and historical prices from SQLite
- Runs target-asset signal generation and backtesting
- Adds cache freshness handling, manual refresh control, and cleaner presentation

Design goals:
- explicit asset selection
- deterministic DB reads
- cache freshness awareness
- honest metrics
- cleaner research UX
- interview/GitHub-readable presentation
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from src.strategies.whale_signals import analyze_whale_flow, backtest_whale_strategy


# ==========================================
# GLOBAL PROJECT PATHS
# ==========================================
ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "db" / "whale_data.db"

SUPPORTED_UI_ASSETS = ["ETH", "WBTC"]
CACHE_TTL_SECONDS = 300  # 5 minutes


# ==========================================
# PAGE SETUP
# ==========================================
st.set_page_config(
    page_title="Whale Flow Research Engine",
    layout="wide",
)

st.title("Whale Flow Research Engine")
st.caption(
    "Target-asset whale-flow analysis with fixed-hour signal generation and vectorized backtesting."
)


# ==========================================
# UTILITY HELPERS
# ==========================================
def get_db_mtime_ns(db_path: Path = DB_PATH) -> int:
    """
    Return the SQLite file modification time in nanoseconds.
    This is used as a cache key input so cached results refresh when the DB changes.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at: {db_path}")
    return db_path.stat().st_mtime_ns


def ensure_datetime_column(df: pd.DataFrame, column_name: str = "timestamp") -> pd.DataFrame:
    """
    Convert a timestamp column to timezone-aware datetime if it exists.
    """
    out = df.copy()
    if column_name in out.columns:
        out[column_name] = pd.to_datetime(out[column_name], utc=True, errors="coerce")
    return out


def format_preview_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a presentation-friendly copy of the research results.

    Keep underlying numeric values numeric for Streamlit column formatting.
    """
    out = df.copy()

    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
        out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    if "signal" in out.columns:
        out["signal_label"] = out["signal"].map({1: "Long", 0: "Flat", -1: "Short"})

    return out


# ==========================================
# DATA ACCESS
# ==========================================
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def load_table(query: str, db_mtime_ns: int) -> pd.DataFrame:
    """
    Load a SQL query result into a DataFrame from the local SQLite vault.

    db_mtime_ns is included so cache invalidates when the DB file changes.
    """
    _ = db_mtime_ns  # explicit cache-key input

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn)

    return ensure_datetime_column(df, "timestamp")


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def run_analysis(
    target_asset: str,
    window_hours: int,
    min_flow_usd: float,
    cost_per_trade: float,
    db_mtime_ns: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build whale-flow signals and run the backtest for one target asset.
    """
    _ = db_mtime_ns  # explicit cache-key input

    events_df = load_table("SELECT * FROM enriched_whales", db_mtime_ns)
    prices_df = load_table("SELECT * FROM historical_prices", db_mtime_ns)

    signals_df = analyze_whale_flow(
        df=events_df,
        target_asset=target_asset,
        window_hours=window_hours,
        min_flow_usd=min_flow_usd,
        price_df=prices_df,
    )

    results_df = backtest_whale_strategy(
        df=signals_df,
        cost_per_trade=cost_per_trade,
    )

    return signals_df, results_df


# ==========================================
# SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("Research Controls")

if st.sidebar.button(
    "Refresh data",
    type="primary",
    help="Clear cached data and rerun the dashboard.",
):
    st.cache_data.clear()
    st.rerun()

with st.sidebar.form("research_controls"):
    target_asset = st.selectbox(
        "Target asset",
        options=SUPPORTED_UI_ASSETS,
        index=0,
        help="Choose the asset whose hourly market-price series and whale-flow signals you want to study.",
    )

    window_hours = st.slider(
        "Rolling whale-flow window (hours)",
        min_value=1,
        max_value=168,
        value=12,
        step=1,
        help="Larger windows smooth the signal more. Smaller windows react faster.",
    )

    min_flow_usd = st.number_input(
        "Minimum rolling net flow threshold (USD)",
        min_value=0.0,
        value=0.0,
        step=10000.0,
        help="Only take a position when the absolute rolling whale-flow exceeds this threshold.",
    )

    cost_per_trade = st.number_input(
        "Transaction cost per trade",
        min_value=0.0,
        value=0.001,
        step=0.0005,
        format="%.4f",
        help="0.001 means 0.10% cost per position change.",
    )

    st.form_submit_button("Run analysis", type="primary")


# ==========================================
# LOAD BASE TABLES
# ==========================================
try:
    db_mtime_ns = get_db_mtime_ns()
    raw_events_df = load_table("SELECT * FROM enriched_whales", db_mtime_ns)
    raw_prices_df = load_table("SELECT * FROM historical_prices", db_mtime_ns)
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()
except Exception as exc:
    st.error(f"Failed to load local data: {exc}")
    st.stop()

if raw_events_df.empty:
    st.error("The 'enriched_whales' table is empty. Run the data pipeline first.")
    st.stop()

if raw_prices_df.empty:
    st.error("The 'historical_prices' table is empty. Run the price pipeline first.")
    st.stop()


# ==========================================
# RUN STRATEGY
# ==========================================
try:
    signals_df, results_df = run_analysis(
        target_asset=target_asset,
        window_hours=window_hours,
        min_flow_usd=min_flow_usd,
        cost_per_trade=cost_per_trade,
        db_mtime_ns=db_mtime_ns,
    )
except ValueError as exc:
    st.error(f"Strategy configuration error: {exc}")
    st.stop()
except Exception as exc:
    st.error(f"Unexpected strategy failure: {exc}")
    st.stop()

if signals_df.empty or results_df.empty:
    st.error("No research output was produced for the selected configuration.")
    st.stop()


# ==========================================
# DATA FRESHNESS PANEL
# ==========================================
latest_event_ts = (
    raw_events_df["timestamp"].max()
    if "timestamp" in raw_events_df.columns
    else pd.NaT
)

target_prices_df = raw_prices_df[
    raw_prices_df["asset_type"].astype(str).str.upper() == target_asset
].copy()

latest_price_ts = (
    target_prices_df["timestamp"].max()
    if "timestamp" in target_prices_df.columns and not target_prices_df.empty
    else pd.NaT
)

db_last_updated = pd.to_datetime(DB_PATH.stat().st_mtime_ns, unit="ns", utc=True)

st.subheader("Data Freshness")
fresh_col1, fresh_col2, fresh_col3, fresh_col4 = st.columns(4)
fresh_col1.metric("Selected asset", target_asset)
fresh_col2.metric(
    "Latest whale event",
    latest_event_ts.strftime("%Y-%m-%d %H:%M UTC") if pd.notna(latest_event_ts) else "N/A",
)
fresh_col3.metric(
    "Latest market price",
    latest_price_ts.strftime("%Y-%m-%d %H:%M UTC") if pd.notna(latest_price_ts) else "N/A",
)
fresh_col4.metric(
    "DB last updated",
    db_last_updated.strftime("%Y-%m-%d %H:%M UTC"),
)


# ==========================================
# METRICS
# ==========================================
target_event_count = int(
    (raw_events_df["asset_type"].astype(str).str.upper() == target_asset).sum()
)
research_row_count = int(len(results_df))
total_trades = int(results_df["trade_flag"].sum())
final_asset_equity = float(results_df["equity_asset"].iloc[-1])
final_strategy_equity = float(results_df["equity_strategy_net"].iloc[-1])
alpha_vs_buy_hold = final_strategy_equity - final_asset_equity
latest_signal = int(results_df["signal"].iloc[-1])
latest_rolling_flow = float(results_df["rolling_net_flow"].iloc[-1])

signal_label = {1: "Long", 0: "Flat", -1: "Short"}.get(latest_signal, "Unknown")

st.subheader("Research Summary")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Raw target-asset event rows", f"{target_event_count}")
col2.metric("Research frame rows", f"{research_row_count}")
col3.metric("Total trades", f"{total_trades}")
col4.metric("Latest signal", signal_label)

col5, col6, col7, col8 = st.columns(4)
col5.metric("Latest rolling net flow", f"${latest_rolling_flow:,.2f}")
col6.metric("Buy & hold equity", f"{final_asset_equity:.4f}x")
col7.metric("Strategy net equity", f"{final_strategy_equity:.4f}x")
col8.metric("Alpha vs buy & hold", f"{alpha_vs_buy_hold:.4f}x")


# ==========================================
# CHARTS
# ==========================================
st.subheader("Equity Curve Comparison")
equity_chart_df = results_df[["timestamp", "equity_asset", "equity_strategy_net"]].copy()
equity_chart_df = equity_chart_df.set_index("timestamp")
st.line_chart(equity_chart_df, height=320)

st.subheader("Rolling Whale Net Flow")
flow_chart_df = results_df[["timestamp", "rolling_net_flow"]].copy().set_index("timestamp")
st.line_chart(flow_chart_df, height=260)

st.subheader("Hourly Whale USD Volume")
volume_chart_df = results_df[["timestamp", "true_usd_volume"]].copy().set_index("timestamp")
st.line_chart(volume_chart_df, height=260)


# ==========================================
# EXPLANATION PANEL
# ==========================================
st.subheader("How to read this dashboard")
st.write(
    """
    - **Target asset** decides which market-price series is being traded.
    - **Rolling whale net flow** measures recent whale pressure using the selected lookback window.
    - A **positive** rolling net flow produces a long signal.
    - A **negative** rolling net flow produces a short signal.
    - The strategy applies the signal on the **next hour**, not the same hour.
    - Transaction cost is charged when the position changes.
    - This dashboard is a **research tool**, not a direct buy/sell instruction engine.
    """
)


# ==========================================
# TABLE PREVIEWS
# ==========================================
st.subheader("Latest Research Rows")
preview_cols = [
    "timestamp",
    "target_asset",
    "price_usd",
    "pressure_usd",
    "rolling_net_flow",
    "signal",
    "position",
    "asset_return",
    "net_strategy_return",
    "equity_asset",
    "equity_strategy_net",
]
preview_df = format_preview_table(results_df[preview_cols].tail(25))

st.dataframe(
    preview_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "timestamp": st.column_config.TextColumn("Timestamp"),
        "target_asset": st.column_config.TextColumn("Target Asset"),
        "price_usd": st.column_config.NumberColumn("Price (USD)", format="%.4f"),
        "pressure_usd": st.column_config.NumberColumn("Pressure (USD)", format="%.2f"),
        "rolling_net_flow": st.column_config.NumberColumn("Rolling Net Flow", format="%.2f"),
        "signal": st.column_config.NumberColumn("Signal", format="%d"),
        "position": st.column_config.NumberColumn("Position", format="%d"),
        "asset_return": st.column_config.NumberColumn("Asset Return", format="%.6f"),
        "net_strategy_return": st.column_config.NumberColumn("Net Strategy Return", format="%.6f"),
        "equity_asset": st.column_config.NumberColumn("Equity Asset", format="%.4f"),
        "equity_strategy_net": st.column_config.NumberColumn("Equity Strategy Net", format="%.4f"),
        "signal_label": st.column_config.TextColumn("Signal Label"),
    },
)

st.subheader("Signal Distribution")
signal_counts = (
    results_df["signal"]
    .map({1: "Long", 0: "Flat", -1: "Short"})
    .value_counts(dropna=False)
    .rename_axis("signal")
    .reset_index(name="count")
)

st.dataframe(
    signal_counts,
    use_container_width=True,
    hide_index=True,
    column_config={
        "signal": st.column_config.TextColumn("Signal"),
        "count": st.column_config.NumberColumn("Count", format="%d"),
    },
)