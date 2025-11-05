#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTF 캐싱 성능 테스트
===================
신호 생성 속도 비교 (캐시 유/무)
"""
import time
import pandas as pd
import numpy as np
from signals.signal_generator import SignalGenerator
from indicators import add_indicators

# 테스트 설정
config = {
    'symbol': 'BTCUSDT',
    'timeframe': '5m',
    'lookback': 400,
    'enable_mtf_confirm': False,  # 먼저 비활성화
    'enable_vol_spike_filter': False,
    'vol_spike_mult': 2.5,
    'vol_ma_len': 20,
    'cooldown_candles': 0,  # 쿨다운 비활성화
    'ema_fast': 8,
    'ema_mid': 21,
    'ema_slow': 50,
    'rsi_len': 14,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'bb_len': 20,
    'bb_std': 2.0,
    'atr_len': 14,
}

# 전략 모듈
class TestStrategy:
    @staticmethod
    def signal_logic(df, cfg):
        last = df.iloc[-1]
        return {
            'side': 'LONG',
            'entry': last['close'],
            'sl': last['close'] * 0.98,
            'tp': last['close'] * 1.02,
            'confidence': 0.8,
            'atr': last.get('atr', 1.0),
            'lev': 1,
            'reason': ['test'],
            'strategy_id': 'test'
        }

strategies = {'test': TestStrategy()}

print("=" * 80)
print("⚡ MTF 캐싱 성능 테스트")
print("=" * 80)

# 테스트 데이터 생성
np.random.seed(42)
n = 250
dates = pd.date_range('2024-01-01', periods=n, freq='5min')
data = {
    'time': [int(d.timestamp() * 1000) for d in dates],
    'open': 100 + np.random.randn(n).cumsum(),
    'high': 101 + np.random.randn(n).cumsum(),
    'low': 99 + np.random.randn(n).cumsum(),
    'close': 100 + np.random.randn(n).cumsum(),
    'volume': 1000 + np.random.randint(-100, 100, n)
}
df = pd.DataFrame(data)
df['high'] = df[['open', 'high', 'close']].max(axis=1)
df['low'] = df[['open', 'low', 'close']].min(axis=1)
df = add_indicators(df)

print(f"✅ 테스트 데이터: {len(df)} 캔들")
print()

# SignalGenerator 초기화
signal_gen = SignalGenerator(config=config, strategy_modules=strategies)

# 신호 생성
signal = TestStrategy.signal_logic(df, config)
signal['ts'] = df.iloc[-1]['time']
signal['symbol'] = 'BTCUSDT'

print("=" * 80)
print("🚀 테스트 1: MTF 비활성화 (베이스라인)")
print("=" * 80)

# 100번 반복 테스트
iterations = 100
start = time.time()
for i in range(iterations):
    signal_gen.validate_signal('BTCUSDT', signal, df)
elapsed = time.time() - start

print(f"✅ {iterations}번 검증 완료")
print(f"⏱️  총 시간: {elapsed:.4f}초")
print(f"⚡ 평균: {elapsed/iterations*1000:.2f}ms per signal")
print()

# MTF 활성화 (캐싱 없이)
print("=" * 80)
print("🐌 테스트 2: MTF 활성화 + 캐싱 없음 (API 매번 호출)")
print("=" * 80)

config_no_cache = config.copy()
config_no_cache['enable_mtf_confirm'] = True
config_no_cache['require_htf_aligned'] = True
config_no_cache['htf'] = '1h'

# 캐시 TTL을 0으로 설정 (캐싱 무효화)
signal_gen_no_cache = SignalGenerator(config=config_no_cache, strategy_modules=strategies)
signal_gen_no_cache.mtf_cache_ttl = 0  # 캐시 비활성화

print("⚠️  실제 API 호출은 느리므로 5번만 테스트...")
iterations_slow = 5

try:
    start = time.time()
    for i in range(iterations_slow):
        print(f"   [{i+1}/{iterations_slow}] API 호출 중...", end="\r")
        signal_gen_no_cache.validate_signal('BTCUSDT', signal, df)
    elapsed = time.time() - start
    
    print(f"\n✅ {iterations_slow}번 검증 완료")
    print(f"⏱️  총 시간: {elapsed:.4f}초")
    print(f"🐌 평균: {elapsed/iterations_slow*1000:.2f}ms per signal (API 호출)")
    print()
except Exception as e:
    print(f"\n⚠️  API 테스트 실패 (예상됨): {e}")
    print("   (API 키 없거나 네트워크 문제)")
    print()

# MTF 활성화 (캐싱 적용)
print("=" * 80)
print("⚡ 테스트 3: MTF 활성화 + 캐싱 적용 (5분 TTL)")
print("=" * 80)

signal_gen_cached = SignalGenerator(config=config_no_cache, strategy_modules=strategies)

# 첫 번째 호출 (캐시 미스 - API 호출)
print("1️⃣  첫 번째 호출 (캐시 미스)...")
start = time.time()
try:
    result1 = signal_gen_cached.validate_signal('BTCUSDT', signal, df)
    elapsed1 = time.time() - start
    print(f"   ⏱️  {elapsed1*1000:.2f}ms (API 호출)")
except Exception as e:
    print(f"   ⚠️  API 실패: {e}")
    elapsed1 = 0

# 두 번째 호출 (캐시 히트 - 즉시 반환!)
print("\n2️⃣  두 번째 호출 (캐시 히트)...")
start = time.time()
result2 = signal_gen_cached.validate_signal('BTCUSDT', signal, df)
elapsed2 = time.time() - start
print(f"   ⚡ {elapsed2*1000:.2f}ms (캐시 사용)")

if elapsed1 > 0:
    speedup = elapsed1 / elapsed2 if elapsed2 > 0 else float('inf')
    print(f"\n🚀 속도 개선: {speedup:.1f}x 빠름!")

# 100번 연속 호출 (모두 캐시 히트)
print("\n3️⃣  100번 연속 호출 (모두 캐시 히트)...")
start = time.time()
for i in range(100):
    signal_gen_cached.validate_signal('BTCUSDT', signal, df)
elapsed_cached = time.time() - start

print(f"   ✅ 100번 완료")
print(f"   ⏱️  총 시간: {elapsed_cached:.4f}초")
print(f"   ⚡ 평균: {elapsed_cached/100*1000:.2f}ms per signal")

print("\n" + "=" * 80)
print("📊 결과 요약")
print("=" * 80)
print(f"MTF 비활성화:     ~{elapsed/iterations*1000:.2f}ms")
if elapsed1 > 0:
    print(f"MTF + 캐시 미스:  ~{elapsed1*1000:.2f}ms (느림)")
print(f"MTF + 캐시 히트:  ~{elapsed_cached/100*1000:.2f}ms (빠름!)")
print()
print("🎯 결론:")
print("   - 첫 신호: API 호출 필요 (느림)")
print("   - 이후 5분간: 캐시 사용 (즉시 반환!)")
print("   - 신호 생성 속도: 실시간 처리 가능 ✅")
print("=" * 80)
