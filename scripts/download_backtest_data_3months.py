#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3개월 백테스트 데이터 다운로드
================================
10개 심볼, 3개월치 5분봉 데이터
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from binance.client import Client
import time

def download_binance_data(symbol: str, interval: str, start_date: str, end_date: str, output_dir: str):
    """Binance에서 과거 데이터 다운로드"""
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
            
            print(f"  📊 {len(all_klines):,}개", end='\r')
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
    
    # 중복 제거
    df = df.drop_duplicates(subset='timestamp')
    
    # 저장
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    filename = f"{symbol}_{interval}_{start_date}_{end_date}.csv"
    filepath = output_path / filename
    
    df.to_csv(filepath, index=False)
    print(f"✅ 저장 완료: {filepath.name} ({len(df):,}개 캔들)")
    
    return filepath


if __name__ == '__main__':
    # ⭐ 설정: 10개 주요 심볼
    symbols = [
        'BTCUSDT',   # Bitcoin
        'ETHUSDT',   # Ethereum
        'BNBUSDT',   # Binance Coin
        'SOLUSDT',   # Solana
        'XRPUSDT',   # Ripple
        'ADAUSDT',   # Cardano
        'AVAXUSDT',  # Avalanche
        'DOGEUSDT',  # Dogecoin
        'MATICUSDT', # Polygon
        'DOTUSDT',   # Polkadot
    ]
    
    # ⭐ 3개월 데이터 (2025-07-22 ~ 2025-10-22)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    # ⭐ 5분봉만 (백테스트용)
    interval = '5m'
    
    output_dir = 'data'
    
    print("="*60)
    print("📥 3개월 백테스트 데이터 다운로드")
    print("="*60)
    print(f"기간: {start_date} ~ {end_date} (3개월)")
    print(f"심볼: {len(symbols)}개")
    print(f"타임프레임: {interval}")
    print(f"예상 시간: 약 {len(symbols) * 2}분")
    print("="*60)
    print()
    
    success_count = 0
    fail_count = 0
    
    for i, symbol in enumerate(symbols, 1):
        try:
            print(f"[{i}/{len(symbols)}] {symbol}")
            download_binance_data(
                symbol=symbol,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                output_dir=output_dir
            )
            success_count += 1
            print()
        except Exception as e:
            print(f"❌ {symbol} 실패: {e}\n")
            fail_count += 1
    
    print("="*60)
    print(f"✅ 다운로드 완료: {success_count}개 성공, {fail_count}개 실패")
    print("="*60)
