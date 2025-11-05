#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BACKTEST_PERIODS.md 기반 데이터 다운로드
==========================================
대표 레짐 블록 6개 다운로드 (2018~2024)
"""
import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path
from binance.client import Client
import time

# 프로젝트 루트
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# BACKTEST_PERIODS.md 대표 블록
PERIODS = [
    {
        'name': 'bear_2018',
        'desc': '2018 약세장 (손절/리스크 검증)',
        'start': '2018-01-01',
        'end': '2018-12-31',
    },
    {
        'name': 'covid_2020',
        'desc': '2020 코로나 (슬리피지/플래시가드)',
        'start': '2020-02-01',
        'end': '2020-06-30',
    },
    {
        'name': 'halving20_bull',
        'desc': '2020-2021 반감기 강세 (추세/트레일)',
        'start': '2020-05-01',
        'end': '2021-04-30',
    },
    {
        'name': 'luna_ftx_2022',
        'desc': '2022 루나/FTX (시스템 스트레스)',
        'start': '2022-04-01',
        'end': '2022-12-31',
    },
    {
        'name': 'etf_anticip_24',
        'desc': '2023-2024 ETF 기대/승인 (변동성)',
        'start': '2023-10-01',
        'end': '2024-03-31',
    },
    {
        'name': 'halving24_post',
        'desc': '2024 반감기 직후 (반감기 후)',
        'start': '2024-04-01',
        'end': '2024-09-30',
    },
]

# HTF(1h/4h)용 장기 윈도우 (BACKTEST_PERIODS.md 6-1 절)
PERIODS_HTF = [
    {
        'name': 'htf_2018_2019',
        'desc': 'HTF 장기 윈도우 (2018-2019)',
        'start': '2018-01-01',
        'end': '2019-12-31',
    },
    {
        'name': 'htf_2020_2021',
        'desc': 'HTF 장기 윈도우 (2020-2021)',
        'start': '2020-01-01',
        'end': '2021-12-31',
    },
    {
        'name': 'htf_2022_2024',
        'desc': 'HTF 장기 윈도우 (2022-2024)',
        'start': '2022-01-01',
        'end': '2024-12-31',
    },
]


def download_period(symbol: str, interval: str, period: dict, output_dir: str):
    """단일 블록 다운로드"""
    name = period['name']
    desc = period['desc']
    start_date = period['start']
    end_date = period['end']
    
    print(f"\n{'='*70}")
    print(f"📥 {name}: {desc}")
    print(f"   {symbol} {interval} ({start_date} ~ {end_date})")
    print('='*70)
    
    client = Client()
    
    # 날짜 변환
    start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
    
    # 데이터 저장 리스트
    all_klines = []
    current_ts = start_ts
    
    while current_ts < end_ts:
        try:
            klines = client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=current_ts,
                end_str=end_ts,
                limit=1000
            )
            
            if not klines:
                break
            
            all_klines.extend(klines)
            current_ts = klines[-1][0] + 1
            
            print(f"  📊 다운로드 중... {len(all_klines):,}개", end='\r')
            time.sleep(0.2)  # Rate limit 방지
            
        except Exception as e:
            print(f"\n  ⚠️  오류: {e}")
            time.sleep(5)
            continue
    
    # DataFrame 생성
    df = pd.DataFrame(all_klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    
    # 필요한 컬럼만
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    # 타입 변환
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # 컬럼명 변경 (기존 호환성)
    df.rename(columns={'timestamp': 'time'}, inplace=True)
    
    # 저장
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{symbol}_{interval}_{name}.csv"
    filepath = output_path / filename
    
    df.to_csv(filepath, index=False)
    print(f"\n✅ 저장 완료: {filename} ({len(df):,}개 캔들)")
    
    return filepath, len(df)


def main():
    """전체 블록 다운로드"""
    symbol = 'BTCUSDT'
    
    # BACKTEST_PERIODS.md 전략별 권장 timeframe
    # Scalping: 5m, Daytrade/Reversion: 15m, Swing/Breakout: 1h, Trend: 4h
    intervals = ['5m', '15m', '1h', '4h']
    
    output_dir = project_root / 'data' / 'backtest_periods'
    
    print("\n" + "="*70)
    print("📥 BACKTEST_PERIODS.md 기반 데이터 다운로드")
    print("="*70)
    print(f"심볼: {symbol}")
    print(f"타임프레임: {', '.join(intervals)}")
    print(f"블록: {len(PERIODS)}개")
    print("="*70)
    
    results = []
    
    for interval in intervals:
        # 1h/4h는 장기 윈도우 추가 포함
        all_periods = PERIODS + (PERIODS_HTF if interval in ['1h', '4h'] else [])
        for period in all_periods:
            try:
                filepath, count = download_period(
                    symbol=symbol,
                    interval=interval,
                    period=period,
                    output_dir=output_dir
                )
                
                results.append({
                    'interval': interval,
                    'period': period['name'],
                    'desc': period['desc'],
                    'file': filepath.name,
                    'candles': count,
                })
                
            except Exception as e:
                print(f"\n❌ {interval} {period['name']} 실패: {e}")
    
    # 결과 요약
    print("\n" + "="*70)
    print("📊 다운로드 완료 요약")
    print("="*70)
    
    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))
    
    # 요약 저장
    summary_path = output_dir / 'download_summary.csv'
    df_results.to_csv(summary_path, index=False)
    print(f"\n✅ 요약: {summary_path}")
    
    print("\n" + "="*70)
    print("✅ 전체 다운로드 완료!")
    print("="*70)
    print(f"\n다음 단계:")
    print(f"  1. WFA 블록 분할 (Train 8주 + OOS 3주)")
    print(f"  2. 레짐 태깅")
    print(f"  3. 지표 계산")


if __name__ == '__main__':
    main()
