#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
백테스트 데이터 다운로드
2주 데이터만 다운로드 (빠른 테스트)
"""
import os
import shutil
from datetime import datetime, timedelta
from binance.client import Client
import pandas as pd

# Binance Client (API 키 불필요 - 공개 데이터)
client = Client()

# 기간 설정: 최근 2주
end_date = datetime.now()
start_date = end_date - timedelta(days=14)

print("=" * 60)
print("📊 백테스트 데이터 다운로드")
print("=" * 60)
print(f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} (14일)")
print(f"타임프레임: 5m")
print("=" * 60)

# 기존 데이터 백업 (삭제 전에)
if os.path.exists('data'):
    backup_dir = f'data_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    print(f"📦 기존 data/ → {backup_dir}/ 백업 중...")
    shutil.copytree('data', backup_dir)
    print(f"✅ 백업 완료: {backup_dir}/")
    
    # 기존 데이터 삭제
    shutil.rmtree('data')
    print("🗑️  기존 data/ 삭제 완료")

# data 디렉토리 생성
os.makedirs('data', exist_ok=True)

# 심볼 리스트 (Phase 1: BTCUSDT만)
symbols = ['BTCUSDT']

for symbol in symbols:
    print(f"\n📥 {symbol} 다운로드 중...")
    
    try:
        # Binance API로 데이터 가져오기
        klines = client.get_historical_klines(
            symbol,
            Client.KLINE_INTERVAL_5MINUTE,
            start_date.strftime("%d %b %Y"),
            end_date.strftime("%d %b %Y")
        )
        
        # DataFrame 생성
        df = pd.DataFrame(klines, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        # 필요한 컬럼만
        df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
        
        # 데이터 타입 변환
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # CSV 저장
        filename = f"data/{symbol}_5m_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.csv"
        df.to_csv(filename, index=False)
        
        print(f"✅ {symbol}: {len(df):,}개 캔들 저장 → {filename}")
    
    except Exception as e:
        print(f"❌ {symbol} 다운로드 실패: {e}")

print("\n" + "=" * 60)
print("✅ 다운로드 완료!")
print("=" * 60)
print(f"\n다음 단계:")
print(f"1. config.yml 확인 (mode: backtest)")
print(f"2. docker-compose --profile sim up --build -d")
print(f"3. docker logs trading_bot_sim -f")
