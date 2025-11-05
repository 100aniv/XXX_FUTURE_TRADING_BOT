#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WFA 블록 생성 (대표 레짐 블록 기반)
===================================
BACKTEST_PERIODS.md의 대표 블록을 WFA로 분할
Train 8주 + OOS 3주
"""
import sys
import pandas as pd
from pathlib import Path
from datetime import timedelta

# 프로젝트 루트
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 대표 블록 (단기/중기 전략용)
PERIODS = [
    ('bear_2018', '2018 약세장'),
    ('covid_2020', '2020 코로나'),
    ('halving20_bull', '2020-2021 반감기 강세'),
    ('luna_ftx_2022', '2022 루나/FTX'),
    ('etf_anticip_24', '2023-2024 ETF'),
    ('halving24_post', '2024 반감기 직후'),
]

# HTF 장기 윈도우 (1h/4h 전략용)
PERIODS_HTF = [
    ('htf_2018_2019', 'HTF 2018-2019'),
    ('htf_2020_2021', 'HTF 2020-2021'),
    ('htf_2022_2024', 'HTF 2022-2024'),
]


def create_wfa_blocks(input_file: Path, interval: str):
    """
    WFA 블록 생성
    
    Args:
        input_file: 입력 파일 (예: BTCUSDT_15m_bear_2018.csv)
        interval: 타임프레임 (5m, 15m)
    
    Returns:
        생성된 WFA 블록 리스트
    """
    # 데이터 로드
    df = pd.read_csv(input_file)
    df['time'] = pd.to_datetime(df['time'])
    df.sort_values('time', inplace=True)
    
    period_name = input_file.stem.split('_')[-1]  # bear_2018, covid_2020 등
    
    print(f"\n{'='*70}")
    print(f"📊 {period_name} ({interval}) - {len(df):,}개 캔들")
    print('='*70)
    
    # Train/OOS 길이 계산 (통계적 신뢰도 확보: 블록 수 15~25개 목표)
    if interval == '5m':
        train_candles = 8 * 7 * 24 * 12  # 8주 * 7일 * 24시간 * 12 (5분)
        oos_candles = 3 * 7 * 24 * 12    # 3주
    elif interval == '15m':
        # 더 많은 블록 생성: 6주 train + 2주 OOS
        train_candles = 6 * 7 * 24 * 4   # 6주 * 7일 * 24시간 * 4 (15분)
        oos_candles = 2 * 7 * 24 * 4     # 2주
    elif interval == '1h':
        # Swing/Breakout: Train 3개월, OOS 1.5개월 (더 많은 블록)
        train_candles = 3 * 30 * 24      # 3개월 * 30일 * 24시간
        oos_candles = int(1.5 * 30 * 24)  # 1.5개월
    elif interval == '4h':
        # Trend: Train 6개월, OOS 3개월 (더 많은 블록)
        train_candles = 6 * 30 * 6       # 6개월 * 30일 * 6 (4시간)
        oos_candles = 3 * 30 * 6         # 3개월
    else:
        raise ValueError(f"Unsupported interval: {interval}")
    
    block_size = train_candles + oos_candles
    
    # WFA 블록 생성
    wfa_blocks = []
    block_idx = 1
    
    start_idx = 0
    while start_idx + block_size <= len(df):
        train_end_idx = start_idx + train_candles
        oos_end_idx = start_idx + block_size
        
        # Train
        train_df = df.iloc[start_idx:train_end_idx].copy()
        train_start = train_df['time'].min()
        train_end = train_df['time'].max()
        
        # OOS
        oos_df = df.iloc[train_end_idx:oos_end_idx].copy()
        oos_start = oos_df['time'].min()
        oos_end = oos_df['time'].max()
        
        # 저장
        output_dir = project_root / 'data' / 'wfa_blocks'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        train_file = output_dir / f"BTCUSDT_{interval}_{period_name}_WFA{block_idx:02d}_TRAIN.csv"
        oos_file = output_dir / f"BTCUSDT_{interval}_{period_name}_WFA{block_idx:02d}_OOS.csv"
        
        train_df.to_csv(train_file, index=False)
        oos_df.to_csv(oos_file, index=False)
        
        wfa_blocks.append({
            'period': period_name,
            'interval': interval,
            'wfa_idx': block_idx,
            'train_file': train_file.name,
            'train_candles': len(train_df),
            'train_start': train_start.strftime('%Y-%m-%d'),
            'train_end': train_end.strftime('%Y-%m-%d'),
            'oos_file': oos_file.name,
            'oos_candles': len(oos_df),
            'oos_start': oos_start.strftime('%Y-%m-%d'),
            'oos_end': oos_end.strftime('%Y-%m-%d'),
        })
        
        print(f"  ✅ WFA{block_idx:02d}: Train {len(train_df):,}개 ({train_start:%Y-%m-%d} ~ {train_end:%Y-%m-%d}) | OOS {len(oos_df):,}개 ({oos_start:%Y-%m-%d} ~ {oos_end:%Y-%m-%d})")
        
        # 다음 블록 (OOS 끝부터 시작)
        start_idx = oos_end_idx
        block_idx += 1
    
    return wfa_blocks


def main():
    """전체 WFA 블록 생성"""
    input_dir = project_root / 'data' / 'backtest_periods'
    
    # BACKTEST_PERIODS.md: 모든 전략 timeframe 지원
    # Scalping(5m), Daytrade/Reversion(15m), Swing/Breakout(1h), Trend(4h)
    intervals = ['5m', '15m', '1h', '4h']
    
    print("\n" + "="*70)
    print("📊 WFA 블록 생성 (대표 레짐 블록 기반)")
    print("="*70)
    print(f"타임프레임: {', '.join(intervals)}")
    print(f"블록 크기: 5m/15m(8주+3주OOS), 1h(6개월+3개월OOS), 4h(12개월+3개월OOS)")
    print("="*70)
    
    all_blocks = []
    
    for interval in intervals:
        # 1h/4h는 HTF 장기 윈도우도 포함
        all_periods = PERIODS + (PERIODS_HTF if interval in ['1h', '4h'] else [])
        
        for period_name, period_desc in all_periods:
            input_file = input_dir / f"BTCUSDT_{interval}_{period_name}.csv"
            
            if not input_file.exists():
                print(f"⚠️  파일 없음: {input_file.name}")
                continue
            
            blocks = create_wfa_blocks(input_file, interval)
            all_blocks.extend(blocks)
    
    # 요약
    print("\n" + "="*70)
    print("📊 WFA 블록 생성 완료")
    print("="*70)
    
    df_blocks = pd.DataFrame(all_blocks)
    print(df_blocks.to_string(index=False))
    
    # 저장
    summary_path = project_root / 'data' / 'wfa_blocks' / 'wfa_blocks_summary.csv'
    df_blocks.to_csv(summary_path, index=False)
    print(f"\n✅ 요약: {summary_path}")
    
    print("\n" + "="*70)
    print("✅ 전체 WFA 블록 생성 완료!")
    print("="*70)
    print(f"\n생성된 블록: {len(all_blocks)}개")
    print(f"\n다음 단계:")
    print(f"  1. 레짐 태깅")
    print(f"  2. 지표 계산")
    print(f"  3. config.yml 타임프레임 변경 (5m → 15m)")
    print(f"  4. WFA 블록 순차 백테스트")


if __name__ == '__main__':
    main()
