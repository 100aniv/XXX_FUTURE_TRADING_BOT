#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Golden Dataset Generator
=========================
백테스트 데이터로부터 골든 데이터셋 생성 (300 rows)
"""
import pandas as pd
from pathlib import Path

# 소스 파일
source_file = Path("data/backtest_periods/BTCUSDT_15m_covid_2020.csv")

# 타겟 파일
target_dir = Path("data/golden")
target_dir.mkdir(parents=True, exist_ok=True)
target_file = target_dir / "BTCUSDT_15m_golden_300.csv"

# 데이터 로드 및 300줄 추출
df = pd.read_csv(source_file)
print(f"원본 파일: {source_file}")
print(f"전체 rows: {len(df)}")
print(f"컬럼: {list(df.columns)}")

# 첫 300줄 추출
df_golden = df.head(300).copy()

# 컬럼명 통일 (time → timestamp)
if 'time' in df_golden.columns:
    df_golden = df_golden.rename(columns={'time': 'timestamp'})

# 저장
df_golden.to_csv(target_file, index=False)
print(f"\n✅ 골든 데이터셋 생성 완료")
print(f"파일: {target_file}")
print(f"Rows: {len(df_golden)}")
print(f"\n첫 5줄:")
print(df_golden.head())
