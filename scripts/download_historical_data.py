#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Historical Data Downloader
===========================
Binance에서 과거 데이터 다운로드 (10년치)
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from binance.client import Client
import time

def download_binance_data(symbol: str, interval: str, start_date: str, end_date: str, output_dir: str):
    """
    Binance에서 과거 데이터 다운로드
    
    Args:
        symbol: 심볼 (예: BTCUSDT)
        interval: 타임프레임 (1m, 5m, 15m, 1h, 4h, 1d)
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
        output_dir: 저장 디렉토리
    """
    client = Client()
    
    print(f"📥 다운로드 시작: {symbol} {interval} ({start_date} ~ {end_date})")
    
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
            
            print(f"  📊 다운로드 중... {len(all_klines):,}개")
            time.sleep(0.5)  # Rate limit 방지
            
        except Exception as e:
            print(f"  ⚠️  오류: {e}")
            time.sleep(5)
            continue
    
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
    
    # 저장
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{symbol}_{interval}_{start_date}_{end_date}.csv"
    filepath = output_path / filename
    
    df.to_csv(filepath, index=False)
    print(f"✅ 저장 완료: {filepath} ({len(df):,}개 캔들)")
    
    return filepath


if __name__ == '__main__':
    # 설정
    symbols = ['BTCUSDT', 'ETHUSDT']
    intervals = ['5m', '15m', '1h', '4h']
    
    # 10년치 데이터 다운로드
    start_date = '2015-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    output_dir = 'data/historical'
    
    print("="*60)
    print("📥 Historical Data Download")
    print("="*60)
    print(f"기간: {start_date} ~ {end_date}")
    print(f"심볼: {', '.join(symbols)}")
    print(f"타임프레임: {', '.join(intervals)}")
    print("="*60)
    
    for symbol in symbols:
        for interval in intervals:
            try:
                download_binance_data(
                    symbol=symbol,
                    interval=interval,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=output_dir
                )
                print()
            except Exception as e:
                print(f"❌ {symbol} {interval} 실패: {e}\n")
    
    print("="*60)
    print("✅ 전체 다운로드 완료!")
    print("="*60)
