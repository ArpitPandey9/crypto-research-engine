"""Generate the V4 context-conditioned outcome summary sample.

This script reads the V3 event-time context sample and writes a grouped V4
summary. It does not create new signals and does not modify the source
validation records.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.context_conditioned_outcomes import (  # noqa: E402
    build_context_conditioned_summary,
)


DEFAULT_INPUT_PATH = Path("data/samples/event_time_context_v3_sample.csv")
DEFAULT_OUTPUT_PATH = Path("data/samples/context_conditioned_outcomes_v4_sample.csv")


def run_context_conditioned_outcomes(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> pd.DataFrame:
    """Build and export the context-conditioned outcome summary."""

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    context_rows = pd.read_csv(input_path)
    summary = build_context_conditioned_summary(context_rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_path, index=False)

    return summary


if __name__ == "__main__":
    result = run_context_conditioned_outcomes()

    print(f"INPUT: {DEFAULT_INPUT_PATH}")
    print(f"OUTPUT: {DEFAULT_OUTPUT_PATH}")
    print(f"ROWS: {len(result)}")
    print()
    print(result.to_string(index=False))
