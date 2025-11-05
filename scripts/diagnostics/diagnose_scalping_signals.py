#!/usr/bin/env python3
"""
Scalping 무신호 진단 스크립트 (.windsurfrules 준수 - 코드 변경 없이 분석만)

목적: 왜 신호가 안 나오는지 조건별 충족률 분석
- 전략 로직 변경 없음
- 설정 변경 없음
- 순수 분석만
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load .env first
from dotenv import load_dotenv
load_dotenv()

import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collectors.rest_collector import fetch_history
from strategies.scalping import signal_logic
from indicators.core_indicators import add_indicators

# Config 로드
with open('config.yml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

scalping_config = config['strategies']['scalping']
lookback = config.get('lookback', 100)
min_bars = config.get('min_bars_for_signal', 50)

# Top 10 symbols for analysis (Paper mode default symbols)
symbols = [
    'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
    'ADAUSDT', 'DOGEUSDT', 'DOTUSDT', 'MATICUSDT', 'LTCUSDT'
]

print("=" * 80)
print("🔍 Scalping 무신호 진단 (코드 변경 없음)")
print("=" * 80)
print(f"\n📋 설정:")
print(f"   - 심볼: {len(symbols)}개")
print(f"   - 타임프레임: {scalping_config['timeframe']}")
print(f"   - Lookback: {lookback}")
print(f"   - Min bars: {min_bars}")
print(f"   - Volume spike: {scalping_config.get('volume_spike', False)}")
print(f"   - Volume mult: {scalping_config.get('volume_mult', 1.0)}")

# 데이터 수집
results = []

print(f"\n📊 신호 조건 분석 중...")
print("-" * 80)

for i, symbol in enumerate(symbols, 1):
    try:
        # 히스토리 로드 (최근 200개)
        klines = fetch_history(
            symbol=symbol,
            timeframe=scalping_config['timeframe'],
            limit=200
        )
        
        if len(klines) < lookback:
            print(f"[{i:2d}/{len(symbols)}] {symbol:10s} ⚠️ 데이터 부족 ({len(klines)}개)")
            continue
        
        # DataFrame 생성
        df = pd.DataFrame(klines, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base', 
            'taker_buy_quote', 'ignore'
        ])
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        
        # 지표 추가
        df = add_indicators(df)
        
        # 최근 캔들만
        recent = df.iloc[-1]
        
        # 조건 체크
        checks = {}
        
        # 1. 기본 지표 존재
        required_indicators = ['ema_fast', 'ema_mid', 'ema_slow', 'bb_upper', 'bb_lower', 'rsi']
        checks['indicators_exist'] = all(ind in df.columns for ind in required_indicators)
        
        # 2. EMA 정렬 (LONG)
        if checks['indicators_exist']:
            ema_fast = recent['ema_fast']
            ema_mid = recent['ema_mid']
            ema_slow = recent['ema_slow']
            checks['ema_aligned_long'] = (ema_fast > ema_mid > ema_slow)
            checks['ema_aligned_short'] = (ema_fast < ema_mid < ema_slow)
        
        # 3. BB 반등
        if checks['indicators_exist']:
            close = recent['close']
            bb_lower = recent['bb_lower']
            bb_upper = recent['bb_upper']
            checks['bb_bounce_long'] = (close <= bb_lower * 1.001)
            checks['bb_bounce_short'] = (close >= bb_upper * 0.999)
        
        # 4. RSI 조건
        if 'rsi' in df.columns:
            rsi = recent['rsi']
            checks['rsi_oversold'] = (20 <= rsi <= 40)
            checks['rsi_overbought'] = (60 <= rsi <= 80)
        
        # 5. Volume spike (설정된 경우)
        if scalping_config.get('volume_spike', False):
            volume_mult = scalping_config.get('volume_mult', 1.5)
            if 'volume' in df.columns and len(df) > 20:
                avg_volume = df['volume'].rolling(20).mean().iloc[-1]
                current_volume = recent['volume']
                checks['volume_spike'] = (current_volume >= avg_volume * volume_mult)
            else:
                checks['volume_spike'] = False
        else:
            checks['volume_spike'] = True  # 조건 없으면 통과
        
        # 실제 신호 생성 시도
        signal = signal_logic(df.copy(), scalping_config)
        has_signal = (signal.get('side') in ['LONG', 'SHORT'])
        
        # 결과 저장
        result = {
            'symbol': symbol,
            'candles': len(df),
            'has_signal': has_signal,
            'signal_side': signal.get('side', 'NONE'),
            **checks
        }
        results.append(result)
        
        # 출력
        status = "🟢 SIGNAL" if has_signal else "⚪ NONE"
        signal_info = f"({signal.get('side', 'NONE')})" if has_signal else ""
        print(f"[{i:2d}/{len(symbols)}] {symbol:10s} {status:12s} {signal_info}")
        
    except Exception as e:
        print(f"[{i:2d}/{len(symbols)}] {symbol:10s} ❌ 에러: {e}")

# 통계 계산
print("\n" + "=" * 80)
print("📊 조건 충족률 분석")
print("=" * 80)

if results:
    df_results = pd.DataFrame(results)
    
    total = len(df_results)
    signal_count = df_results['has_signal'].sum()
    
    print(f"\n총 분석: {total}개 심볼")
    print(f"신호 발생: {signal_count}개 ({signal_count/total*100:.1f}%)")
    
    if signal_count > 0:
        print(f"\n신호 방향:")
        for side, count in df_results[df_results['has_signal']].groupby('signal_side').size().items():
            print(f"   {side}: {count}개")
    
    print(f"\n조건별 충족률:")
    condition_cols = [col for col in df_results.columns if col not in ['symbol', 'candles', 'has_signal', 'signal_side']]
    
    for col in condition_cols:
        if col in df_results.columns:
            pass_count = df_results[col].sum()
            pass_rate = pass_count / total * 100
            status = "✅" if pass_rate > 50 else "⚠️" if pass_rate > 10 else "❌"
            print(f"   {status} {col:25s}: {pass_count:2d}/{total} ({pass_rate:5.1f}%)")
    
    # 모든 조건 충족
    if condition_cols:
        all_conditions = df_results[condition_cols].all(axis=1).sum()
        all_rate = all_conditions / total * 100
        print(f"\n   🎯 모든 조건 충족: {all_conditions}/{total} ({all_rate:.1f}%)")
    
    # 권장사항
    print("\n" + "=" * 80)
    print("💡 분석 결과")
    print("=" * 80)
    
    if signal_count == 0:
        print("\n⚠️ 신호 없음 - 조건이 너무 엄격합니다.")
        print("\n🔧 권장 조치 (우선순위순):")
        print("   1. Config 완화 (전략 로직 변경 없이):")
        print("      - volume_spike: false (또는 volume_mult 낮추기)")
        print("      - RSI 범위 확대")
        print("      - BB 반등 허용 범위 확대")
        print("   2. 백테스트로 신호 빈도 검증")
        print("   3. 심볼 확대 (100개 → 더 많은 기회)")
    else:
        print(f"\n✅ 정상 - {signal_count}개 심볼에서 신호 발생")
        print("\n💡 참고:")
        print("   - Paper 모드에서 시간이 지나면 거래 발생 가능")
        print("   - 포트폴리오 제약으로 일부 신호 거부될 수 있음")

else:
    print("\n❌ 분석 실패 - 데이터 없음")

print("\n" + "=" * 80)
print("✅ 진단 완료")
print("=" * 80)
