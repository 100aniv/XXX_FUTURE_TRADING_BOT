#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
샘플 백테스트 데이터 생성
빠른 테스트를 위한 BTCUSDT 5m 데이터 생성
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# 데이터 설정
START_DATE = "2024-07-01"
END_DATE = "2024-10-17"
SYMBOL = "BTCUSDT"
INTERVAL = "5m"

# 기본 가격 (BTC)
BASE_PRICE = 60000

def generate_sample_data():
    """샘플 OHLCV 데이터 생성"""
    
    # 날짜 범위
    start = pd.to_datetime(START_DATE)
    end = pd.to_datetime(END_DATE)
    
    # 5분봉 생성
    timestamps = pd.date_range(start=start, end=end, freq='5min')
    
    print(f"📊 샘플 데이터 생성 중...")
    print(f"   기간: {START_DATE} ~ {END_DATE}")
    print(f"   봉 개수: {len(timestamps):,}개")
    
    # 가격 데이터 생성 (현실적인 변동)
    np.random.seed(42)
    
    # 트렌드 + 노이즈
    trend = np.linspace(0, 10000, len(timestamps))  # 상승 트렌드
    noise = np.random.randn(len(timestamps)) * 1000  # 노이즈
    
    close_prices = BASE_PRICE + trend + noise
    
    # OHLC 생성
    data = []
    for i, ts in enumerate(timestamps):
        close = close_prices[i]
        
        # Open: 이전 Close 또는 현재 Close 근처
        open_price = close_prices[i-1] if i > 0 else close
        open_price += np.random.randn() * 50
        
        # High/Low: Open과 Close 범위 내
        high = max(open_price, close) + abs(np.random.randn() * 100)
        low = min(open_price, close) - abs(np.random.randn() * 100)
        
        # Volume
        volume = np.random.uniform(100, 1000)
        
        data.append({
            'timestamp': ts,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    
    # 저장
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    filename = f"{SYMBOL}_{INTERVAL}_{START_DATE}_{END_DATE}.csv"
    filepath = data_dir / filename
    
    df.to_csv(filepath, index=False)
    
    print(f"✅ 샘플 데이터 생성 완료!")
    print(f"💾 파일: {filepath}")
    print(f"📊 크기: {len(df):,} rows")
    print(f"💰 가격 범위: ${df['close'].min():.2f} ~ ${df['close'].max():.2f}")
    
    return filepath

if __name__ == "__main__":
    generate_sample_data()
