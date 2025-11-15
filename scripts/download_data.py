#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE9-7: 범용 데이터 다운로더 (CLI 지원)
==========================================
Binance에서 과거 데이터 다운로드

⭐ 기존 download_historical_data.py를 기반으로 CLI 인자 지원 추가
⭐ 최소 변경 원칙: 기존 로직 재활용, argparse만 추가

사용법:
    python scripts/download_data.py \
        --symbol BTCUSDT \
        --timeframe 1m \
        --start-date 2024-10-01 \
        --end-date 2024-12-31 \
        --output-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from binance.client import Client
import time


def download_binance_data(symbol: str, interval: str, start_date: str, end_date: str, output_path: str = None):
    """
    Binance에서 과거 데이터 다운로드
    
    Args:
        symbol: 심볼 (예: BTCUSDT)
        interval: 타임프레임 (1m, 5m, 15m, 1h, 4h, 1d)
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
        output_path: 저장 경로 (None이면 자동 생성)
    
    Returns:
        저장된 파일 경로
    """
    client = Client()
    
    print("=" * 70)
    print(f"📥 다운로드 시작: {symbol} {interval} ({start_date} ~ {end_date})")
    print("=" * 70)
    
    # 날짜 변환
    start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
    
    # 데이터 저장 리스트
    all_klines = []
    
    # 청크로 다운로드 (Binance API 제한: 1000개/요청)
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
            current_ts = klines[-1][0] + 1  # 다음 시작점
            
            print(f"  📊 다운로드 중... {len(all_klines):,}개", end='\r')
            time.sleep(0.5)  # Rate limit 방지
            
        except Exception as e:
            print(f"\n  ⚠️  오류: {e}")
            time.sleep(5)
            continue
    
    print()  # 줄바꿈
    
    # DataFrame 생성
    df = pd.DataFrame(all_klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    
    # 필요한 컬럼만 선택
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    
    # 타입 변환
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    # ⭐ PHASE9-7: 컬럼명 변경 (timestamp → time)
    # HistoricalFeed가 기대하는 포맷과 일치시킴
    df = df.rename(columns={'timestamp': 'time'})
    
    # 저장 경로 결정
    if output_path is None:
        # 자동 생성: data/{symbol}_{interval}_{start_date}_{end_date}.csv
        output_dir = Path('data')
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{symbol}_{interval}_{start_date}_{end_date}.csv"
        filepath = output_dir / filename
    else:
        # 사용자 지정 경로
        filepath = Path(output_path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # CSV 저장
    df.to_csv(filepath, index=False)
    
    print("=" * 70)
    print(f"✅ 저장 완료: {filepath}")
    print(f"   - 캔들 수: {len(df):,}개")
    print(f"   - 기간: {df['time'].iloc[0]} ~ {df['time'].iloc[-1]}")
    print(f"   - 컬럼: {', '.join(df.columns)}")
    print("=" * 70)
    
    return filepath


def main():
    """CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description='Binance 데이터 다운로더 (PHASE9-7)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
    # 1분봉 3개월 데이터
    python scripts/download_data.py \\
        --symbol BTCUSDT \\
        --timeframe 1m \\
        --start-date 2024-10-01 \\
        --end-date 2024-12-31 \\
        --output-path data/BTCUSDT_1m_2024-10-01_2024-12-31_OOS.csv
    
    # 5분봉 1년 데이터 (자동 경로)
    python scripts/download_data.py \\
        --symbol BTCUSDT \\
        --timeframe 5m \\
        --start-date 2024-01-01 \\
        --end-date 2024-12-31
        """
    )
    
    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='심볼 (예: BTCUSDT, ETHUSDT)'
    )
    
    parser.add_argument(
        '--timeframe',
        type=str,
        required=True,
        help='타임프레임 (1m, 5m, 15m, 1h, 4h, 1d)'
    )
    
    parser.add_argument(
        '--start-date',
        type=str,
        required=True,
        help='시작 날짜 (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        type=str,
        required=True,
        help='종료 날짜 (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--output-path',
        type=str,
        default=None,
        help='저장 경로 (지정하지 않으면 data/{symbol}_{timeframe}_{start}_{end}.csv)'
    )
    
    args = parser.parse_args()
    
    try:
        filepath = download_binance_data(
            symbol=args.symbol,
            interval=args.timeframe,
            start_date=args.start_date,
            end_date=args.end_date,
            output_path=args.output_path
        )
        
        print()
        print("🎉 다운로드 완료!")
        print(f"📁 파일: {filepath}")
        print()
        print("다음 단계:")
        print(f"  백테스트 실행:")
        print(f"    python scripts/run_backtest.py \\")
        print(f"      --mode backtest_raw \\")
        print(f"      --strategy scalping \\")
        print(f"      --symbol {args.symbol} \\")
        print(f"      --timeframe {args.timeframe} \\")
        print(f"      --start-date {args.start_date} \\")
        print(f"      --end-date {args.end_date} \\")
        print(f"      --data-path {filepath}")
        
        return 0
        
    except Exception as e:
        print()
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
