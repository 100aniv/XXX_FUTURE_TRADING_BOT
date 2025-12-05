#!/usr/bin/env python3
import pandas as pd
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
data_file = project_root / "data" / "BTCUSDT_5m_2024-01-01_2024-12-31.csv"

df = pd.read_csv(data_file)
print(f"First: {df['timestamp'].min()}")
print(f"Last: {df['timestamp'].max()}")
print(f"Total rows: {len(df)}")
print(f"\nSample rows around 2024-12-08:")
df_sample = df[df['timestamp'].str.contains('2024-12-08')]
print(df_sample.head(10))
