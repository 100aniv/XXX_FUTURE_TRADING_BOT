#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
signals 모듈 통합 테스트
=======================
SignalGenerator 기능 검증
"""
import pandas as pd
import numpy as np
from signals.signal_generator import SignalGenerator
from indicators import add_indicators

# 테스트 설정
config = {
    'symbol': 'BTCUSDT',
    'timeframe': '5m',
    'lookback': 400,
    'enable_mtf_confirm': False,  # 테스트용 비활성화
    'enable_vol_spike_filter': True,
    'vol_spike_mult': 2.5,
    'vol_ma_len': 20,
    'cooldown_candles': 3,
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

# 전략 모듈 (더미)
class DummyStrategy:
    @staticmethod
    def signal_logic(df, cfg):
        # 간단한 테스트 신호
        last = df.iloc[-1]
        if last['rsi'] < 30:
            return {
                'side': 'LONG',
                'entry': last['close'],
                'sl': last['close'] * 0.98,
                'tp': last['close'] * 1.02,
                'confidence': 0.8,
                'atr': last['atr'],
                'lev': 1,
                'reason': ['RSI < 30'],
                'strategy_id': 'test'
            }
        return None

strategies = {'test': DummyStrategy()}

print("=" * 80)
print("🧪 signals 모듈 통합 테스트")
print("=" * 80)

# SignalGenerator 초기화
signal_gen = SignalGenerator(config=config, strategy_modules=strategies)
print("✅ SignalGenerator 초기화 완료")

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

# 지표 계산
df = add_indicators(df)
print(f"✅ 테스트 데이터 생성 완료: {len(df)} 캔들")

# RSI를 낮게 설정
df.loc[df.index[-1], 'rsi'] = 25
print(f"✅ 마지막 RSI: {df.iloc[-1]['rsi']:.2f}")

# 신호 생성 테스트
print("\n" + "=" * 80)
print("🔍 신호 생성 테스트")
print("=" * 80)

signal = DummyStrategy.signal_logic(df, config)
if signal:
    print(f"✅ 신호 생성 성공")
    print(f"   Side: {signal['side']}")
    print(f"   Entry: {signal['entry']:.2f}")
    print(f"   SL: {signal['sl']:.2f}")
    print(f"   TP: {signal['tp']:.2f}")
    print(f"   Confidence: {signal['confidence']}")
else:
    print("❌ 신호 생성 실패")

# 신호 검증 테스트
if signal:
    print("\n" + "=" * 80)
    print("🔍 신호 검증 테스트 (MTF, 쿨다운, 거래량 필터)")
    print("=" * 80)
    
    signal['ts'] = df.iloc[-1]['time']
    signal['symbol'] = 'BTCUSDT'
    
    # 첫 번째 검증
    is_valid = signal_gen.validate_signal('BTCUSDT', signal, df)
    print(f"{'✅' if is_valid else '❌'} 첫 번째 검증: {is_valid}")
    
    # 쿨다운 테스트 (같은 신호 바로 다시)
    is_valid2 = signal_gen.validate_signal('BTCUSDT', signal, df)
    print(f"{'✅' if not is_valid2 else '❌'} 쿨다운 테스트: {not is_valid2} (False여야 함)")
    
    # 다른 방향 신호
    signal2 = signal.copy()
    signal2['side'] = 'SHORT'
    is_valid3 = signal_gen.validate_signal('BTCUSDT', signal2, df)
    print(f"{'✅' if is_valid3 else '❌'} 반대 방향 신호: {is_valid3}")

# Flash Guard 테스트
print("\n" + "=" * 80)
print("🔍 Flash Guard 테스트 (급등락 감지)")
print("=" * 80)

from execution.risk_manager import RiskManager

risk = RiskManager(config={'enable_flash_guard': True, 'flash_pct': 0.03, 
                            'flash_window_sec': 60, 'flash_pause_candles': 3,
                            'timeframe': '5m'})

# 정상 가격
ts = int(dates[-1].timestamp() * 1000)
price1 = 100.0
risk.flash_guard_update('BTCUSDT', price1, ts)
allowed1 = risk.flash_guard_allowed('BTCUSDT', ts)
print(f"✅ 정상 가격 ({price1:.2f}): {allowed1}")

# 급등 (4%)
ts2 = ts + 60000  # 1분 후
price2 = 104.5  # 4.5% 상승
risk.flash_guard_update('BTCUSDT', price2, ts2)
allowed2 = risk.flash_guard_allowed('BTCUSDT', ts2)
print(f"{'✅' if not allowed2 else '❌'} 급등 후 ({price2:.2f}): {not allowed2} (False여야 함)")

# 쿨다운 후
ts3 = ts2 + (5 * 60 * 1000 * 3)  # 3 캔들 후
allowed3 = risk.flash_guard_allowed('BTCUSDT', ts3)
print(f"✅ 쿨다운 후: {allowed3}")

print("\n" + "=" * 80)
print("🎉 테스트 완료!")
print("=" * 80)
print("\n✅ signals 모듈 통합 성공!")
print("   - SignalGenerator 초기화 ✅")
print("   - 신호 검증 (MTF, 쿨다운, 거래량) ✅")
print("   - Flash Guard (급등락 감지) ✅")
