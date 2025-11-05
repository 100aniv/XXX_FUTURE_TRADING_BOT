#!/usr/bin/env python3
"""PositionSizer 테스트 - common.calculations 통합 확인"""

from execution.position_sizer import PositionSizer

# 1. 기본 테스트
ps = PositionSizer()

signal = {
    'entry_price': 60000,
    'sl_price': 59400,  # 1% 손절
    'confidence': 0.8
}

qty, meta = ps.calculate(signal)

print("="*60)
print("✅ PositionSizer 테스트 (common.calculations 통합)")
print("="*60)
print(f"Entry: ${signal['entry_price']:,.0f}")
print(f"SL: ${signal['sl_price']:,.0f}")
print(f"Stop Distance: ${meta['stop_distance']:,.2f} ({meta['stop_distance']/signal['entry_price']*100:.2f}%)")
print(f"Risk USDT: ${meta['risk_usdt']:,.2f}")
print(f"Base Qty: {meta['base_qty']:.4f} BTC")
print(f"Quality Weight: {meta['quality_weight']:.2f}")
print(f"Final Qty: {qty:.4f} BTC")
print(f"Position Value: ${meta['position_value']:,.2f}")
print("="*60)

# 검증
assert qty > 0, "수량이 0보다 커야 함"
assert meta['risk_usdt'] == 100.0, "리스크는 $100이어야 함 (1% of 10,000)"
print("✅ 모든 테스트 통과!")
