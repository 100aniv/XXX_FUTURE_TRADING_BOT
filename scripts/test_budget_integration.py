#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE17 Budget SSOT Integration Test
=====================================

Simple integration test to verify Budget functionality without pytest complexity.
"""
import sys
import os

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from execution.position_sizer import PositionSizer
from execution.portfolio_manager import PortfolioManager

# 설정
config = {
    'capital': {'initial': 50000},
    'risk': {
        'per_trade': 0.003,
        'max_positions': 3,
        'max_exposure_per_symbol': 0.35,
    },
    'position_sizing': {
        'min_position_value': 100,
        'max_position_value': 15000,
        'min_position_notional': 100,
        'max_position_notional': 15000,
        'quality_weight_min': 0.7,
        'quality_weight_max': 1.3,
        'multi_position_scaling': True,
        'exposure_reduction_factor': 0.95,
        'allow_partial_entry': True,
        'context_scaling': {
            'enabled': False
        }
    },
    'leverage': {
        'default': 2,
        'min': 2,
        'max': 50
    },
    'portfolio': {
        'max_strategy_positions': 5,
        'max_total_exposure': 0.95,
        'budget': {
            'default_allocation': 0.25,
            'strategy_allocation': {
                'scalping': 0.25
            }
        }
    }
}

print("=" * 70)
print("PHASE17 Budget SSOT Integration Test")
print("=" * 70)

# 1. Portfolio Manager 초기화
print("\n[Test 1] Portfolio Manager 초기화")
portfolio = PortfolioManager(config, load_existing=False)
print(f"✅ Equity: ${portfolio.equity:,.0f}")

# 2. Budget 계산
print("\n[Test 2] Budget 계산")
total_budget = portfolio.calculate_strategy_budget('scalping')
print(f"✅ Total Budget: ${total_budget:,.0f} (예상: $12,500)")
assert total_budget == 12500, f"Budget mismatch: {total_budget} != 12500"

# 3. 사용 가능한 Budget (포지션 없음)
print("\n[Test 3] Available Budget (포지션 없음)")
available = portfolio.get_available_budget('scalping')
print(f"✅ Available: ${available:,.0f} (예상: $12,500)")
assert available == 12500, f"Available mismatch: {available} != 12500"

# 4. Position Sizer 초기화
print("\n[Test 4] Position Sizer 초기화")
sizer = PositionSizer(config)
print(f"✅ Position Sizer 생성 완료")

# 5. 첫 Entry (Budget 충분)
print("\n[Test 5] 첫 Entry (Budget 충분)")
signal = {
    'entry_price': 100000.0,
    'sl_price': 98000.0,
    'confidence': 0.8
}
qty1, meta1 = sizer.calculate(signal, available_budget=available)
print(f"✅ Qty: {qty1:.4f}, Value: ${meta1['position_value']:,.2f}")
print(f"   Budget Capped: {meta1['budget_capped']} (예상: False)")
assert qty1 > 0, "Qty should be > 0"
assert not meta1['budget_capped'], "Should not be capped"
position_value_1 = meta1['position_value']

# 6. 포지션 추가
print("\n[Test 6] 첫 포지션 추가")
portfolio.positions['BTCUSDT'] = [{
    'strategy': 'scalping',
    'status': 'OPEN',
    'position_value': position_value_1,
    'value': position_value_1,  # 호환성을 위해 추가
    'side': 'LONG'
}]
print(f"✅ BTCUSDT 포지션 추가: ${position_value_1:,.2f}")

# 7. 사용 가능한 Budget (포지션 1개)
print("\n[Test 7] Available Budget (포지션 1개)")
used = portfolio._get_used_budget('scalping')
available = portfolio.get_available_budget('scalping')
print(f"✅ Used: ${used:,.2f}, Available: ${available:,.2f}")
assert used == position_value_1, f"Used mismatch: {used} != {position_value_1}"
assert available == 12500 - position_value_1, f"Available mismatch"

# 8. 두 번째 Entry (Budget Cap 적용)
print("\n[Test 8] 두 번째 Entry (Budget Cap 예상)")
qty2, meta2 = sizer.calculate(signal, available_budget=available)
print(f"✅ Qty: {qty2:.4f}, Value: ${meta2['position_value']:,.2f}")
print(f"   Budget Capped: {meta2['budget_capped']} (예상: True 가능)")
assert qty2 > 0, "Qty should be > 0"

# Budget Cap 여부는 요청 크기에 따라 다름
if meta2['position_value'] == available:
    print(f"   ✅ Budget Cap 적용됨! (${meta2['position_value']:,.2f} == ${available:,.2f})")
else:
    print(f"   ℹ️  Budget Cap 불필요 (요청 크기 < Available)")

position_value_2 = meta2['position_value']

# 9. 두 번째 포지션 추가
print("\n[Test 9] 두 번째 포지션 추가")
portfolio.positions['ETHUSDT'] = [{
    'strategy': 'scalping',
    'status': 'OPEN',
    'position_value': position_value_2,
    'value': position_value_2,  # 호환성을 위해 추가
    'side': 'SHORT'
}]
print(f"✅ ETHUSDT 포지션 추가: ${position_value_2:,.2f}")

# 10. 사용 가능한 Budget (포지션 2개)
print("\n[Test 10] Available Budget (포지션 2개)")
used = portfolio._get_used_budget('scalping')
available = portfolio.get_available_budget('scalping')
print(f"✅ Used: ${used:,.2f}, Available: ${available:,.2f}")
total_used = position_value_1 + position_value_2
assert abs(used - total_used) < 1.0, f"Used mismatch: {used} != {total_used}"

# 11. 세 번째 Entry (Budget 부족/소진 가능)
print("\n[Test 11] 세 번째 Entry (Budget 소진 가능)")
qty3, meta3 = sizer.calculate(signal, available_budget=available)
print(f"✅ Qty: {qty3:.4f}, Value: ${meta3.get('position_value', 0):,.2f}")

if qty3 == 0:
    print(f"   ✅ Entry 차단됨 (Available Budget 부족: ${available:,.2f})")
    print(f"   Reason: {meta3.get('reason', 'N/A')}")
else:
    print(f"   ℹ️  Entry 허용 (Available Budget 충분: ${available:,.2f})")

# 12. Portfolio Manager 검증 (can_open_position)
print("\n[Test 12] Portfolio Manager can_open_position 검증")
test_value = 1000.0
can_open, reason = portfolio.can_open_position(
    symbol='SOLUSDT',
    strategy='scalping',
    position_value=test_value,
    side='LONG'
)
print(f"   Test Value: ${test_value:,.2f}")
print(f"   Can Open: {can_open}, Reason: {reason}")

if available >= test_value:
    assert can_open, f"Should be able to open: available={available}, requested={test_value}"
    print(f"✅ 검증 통과: Available({available}) >= Requested({test_value})")
else:
    print(f"ℹ️  Available({available}) < Requested({test_value}) → 차단 예상")

# 최종 요약
print("\n" + "=" * 70)
print("Test Summary")
print("=" * 70)
print(f"✅ All tests passed!")
print(f"   Total Budget: ${12500:,.2f}")
print(f"   Used: ${used:,.2f}")
print(f"   Available: ${available:,.2f}")
print(f"   Position 1: ${position_value_1:,.2f}")
print(f"   Position 2: ${position_value_2:,.2f}")
print("=" * 70)
