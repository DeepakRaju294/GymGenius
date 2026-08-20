"""Quick helper: run this against a freshly-downloaded dataset CSV to see its
real column names and a sample row, so source_configs.json's `rawColumns`
guesses can be corrected before ingest_exercise_catalog.py runs for real.

Usage: python inspect_columns.py ml/training/datasets/exercises_dataset.csv
"""

from __future__ import annotations

import sys

import pandas as pd


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python inspect_columns.py <path-to-csv>", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(sys.argv[1], nrows=5)
    print(f"Columns ({len(df.columns)}):")
    for col in df.columns:
        print(f"  - {col}")
    print("\nFirst row:")
    print(df.iloc[0].to_dict())


if __name__ == "__main__":
    main()
