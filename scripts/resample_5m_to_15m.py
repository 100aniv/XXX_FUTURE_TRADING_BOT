#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
5m OHLCV 데이터를 15m으로 리샘플링
====================================
PHASE30-1: btc15m_core_v1 백테스트용 15m 데이터 생성

입력: BTCUSDT_5m_2024-01-01_2024-12-31.csv
출력: BTCUSDT_15m_2024-01-01_2024-12-31.csv
"""
import pandas as pd
import sys
from pathlib import Path

def resample_5m_to_15m(input_csv: str, output_csv: str):
    """
    5m OHLCV를 15m으로 리샘플링
    
    Args:
        input_csv: 입력 5m CSV 경로
        output_csv: 출력 15m CSV 경로
    """
    print(f"=== 5m → 15m 리샘플링 시작 ===")
    print(f"입력: {input_csv}")
    print(f"출력: {output_csv}")
    
    # CSV 로드
    print("\n1. CSV 로드 중...")
    df = pd.read_csv(input_csv)
    
    print(f"   원본 데이터: {len(df):,}개 캔들")
    print(f"   컬럼: {list(df.columns)}")
    print(f"   시작: {df['timestamp'].iloc[0]}")
    print(f"   종료: {df['timestamp'].iloc[-1]}")
    
    # timestamp를 datetime으로 변환
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.set_index('timestamp', inplace=True)
    
    # 15분 리샘플링
    print("\n2. 15m 리샘플링 중...")
    df_15m = df.resample('15T').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })
    
    # NaN 제거 (시장이 닫힌 시간대)
    df_15m.dropna(inplace=True)
    
    print(f"   리샘플링 결과: {len(df_15m):,}개 캔들")
    print(f"   시작: {df_15m.index[0]}")
    print(f"   종료: {df_15m.index[-1]}")
    
    # 검증: 캔들 간격 확인
    time_diffs = df_15m.index.to_series().diff()
    mode_diff = time_diffs.mode()[0]
    print(f"\n3. 검증:")
    print(f"   캔들 간격 (최빈값): {mode_diff}")
    
    if mode_diff != pd.Timedelta('15 minutes'):
        print(f"   ⚠️  경고: 캔들 간격이 15분이 아닙니다!")
    else:
        print(f"   ✅ 캔들 간격 정상 (15분)")
    
    # timestamp를 컬럼으로 되돌리기
    df_15m.reset_index(inplace=True)
    
    # 샘플 출력
    print(f"\n4. 샘플 데이터 (처음 5개):")
    print(df_15m.head().to_string())
    
    # CSV 저장
    print(f"\n5. CSV 저장 중: {output_csv}")
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_15m.to_csv(output_csv, index=False)
    
    print(f"\n✅ 리샘플링 완료!")
    print(f"   파일: {output_csv}")
    print(f"   캔들 수: {len(df_15m):,}개")
    print(f"   기간: {df_15m['timestamp'].iloc[0]} ~ {df_15m['timestamp'].iloc[-1]}")
    
    return df_15m


if __name__ == '__main__':
    input_csv = 'data/BTCUSDT_5m_2024-01-01_2024-12-31.csv'
    output_csv = 'data/BTCUSDT_15m_2024-01-01_2024-12-31.csv'
    
    if len(sys.argv) > 1:
        input_csv = sys.argv[1]
    if len(sys.argv) > 2:
        output_csv = sys.argv[2]
    
    # 파일 존재 확인
    if not Path(input_csv).exists():
        print(f"❌ 입력 파일이 존재하지 않습니다: {input_csv}")
        sys.exit(1)
    
    df_15m = resample_5m_to_15m(input_csv, output_csv)
