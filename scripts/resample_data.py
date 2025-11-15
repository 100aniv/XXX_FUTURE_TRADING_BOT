#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OHLCV Data Resampling Utility
==============================
1m → 3m (or any timeframe) 데이터 리샘플링

Usage:
  python scripts/resample_data.py \
    --input data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv \
    --output data/BTCUSDT_3m_2024-10-01_2024-12-31_OOS.csv \
    --timeframe 3T

OHLCV Resampling Rules:
  - open:   first open in the period
  - high:   max high in the period
  - low:    min low in the period
  - close:  last close in the period
  - volume: sum of volume in the period

Note: 
  - Timeframe format: pandas frequency string (e.g., 3T for 3 minutes)
  - Input CSV must have columns: timestamp, open, high, low, close, volume
"""
import argparse
import pandas as pd
from pathlib import Path


def resample_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    OHLCV 데이터를 지정된 타임프레임으로 리샘플링
    
    Args:
        df: 원본 OHLCV DataFrame (time, open, high, low, close, volume)
        timeframe: pandas frequency string (e.g., '3T' for 3 minutes)
    
    Returns:
        리샘플링된 DataFrame
    """
    # time을 datetime으로 변환하고 인덱스로 설정
    df = df.copy()
    
    # 컬럼명 자동 감지 (time 또는 timestamp)
    time_col = 'time' if 'time' in df.columns else 'timestamp'
    df[time_col] = pd.to_datetime(df[time_col])
    df.set_index(time_col, inplace=True)
    
    # OHLCV 리샘플링 규칙
    resampled = df.resample(timeframe).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    
    # NaN 제거 (불완전한 마지막 캔들 등)
    resampled = resampled.dropna()
    
    # time을 컬럼으로 복원
    resampled.reset_index(inplace=True)
    resampled.rename(columns={resampled.columns[0]: 'time'}, inplace=True)
    
    return resampled


def main():
    parser = argparse.ArgumentParser(
        description='Resample OHLCV data to different timeframe',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input CSV file path (1m data)'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output CSV file path (resampled data)'
    )
    parser.add_argument(
        '--timeframe',
        default='3T',
        help='Target timeframe (pandas frequency string, e.g., 3T for 3 minutes, 5T for 5 minutes)'
    )
    
    args = parser.parse_args()
    
    # 입력 파일 확인
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ ERROR: Input file not found: {args.input}")
        return 1
    
    print(f"📂 Loading data from: {args.input}")
    df = pd.read_csv(args.input)
    
    print(f"📊 Original data: {len(df)} candles")
    print(f"🔄 Resampling to: {args.timeframe}")
    
    # 리샘플링
    resampled = resample_ohlcv(df, args.timeframe)
    
    print(f"✅ Resampled data: {len(resampled)} candles")
    
    # 출력 디렉토리 생성 (필요시)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # CSV 저장
    resampled.to_csv(args.output, index=False)
    print(f"💾 Saved to: {args.output}")
    
    # 샘플 데이터 출력
    print("\n📋 Sample (first 3 rows):")
    print(resampled.head(3))
    
    return 0


if __name__ == '__main__':
    exit(main())
