#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PR12 동적 반올림 및 펀딩 연동 테스트
"""
from common.calculations import (
    get_exchange_info,
    round_tick,
    get_funding_rate,
    calculate_funding_fee
)

def test_exchange_info():
    """exchangeInfo API 테스트"""
    print("=" * 60)
    print("1. exchangeInfo API 테스트")
    print("=" * 60)
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for symbol in symbols:
        info = get_exchange_info(symbol)
        if info:
            print(f"✅ {symbol}: tickSize={info['tickSize']}, stepSize={info['stepSize']}")
        else:
            print(f"❌ {symbol}: API 조회 실패")
    print()

def test_round_tick():
    """동적 반올림 테스트"""
    print("=" * 60)
    print("2. 동적 반올림 테스트")
    print("=" * 60)
    
    test_cases = [
        ("BTCUSDT", 50123.456789),
        ("ETHUSDT", 3456.789123),
        ("SOLUSDT", 123.456789),
    ]
    
    for symbol, price in test_cases:
        rounded_api = round_tick(symbol, price, use_api=True)
        rounded_fallback = round_tick(symbol, price, use_api=False)
        print(f"{symbol}: {price:.6f} → API: {rounded_api:.6f}, Fallback: {rounded_fallback:.6f}")
    print()

def test_funding_rate():
    """fundingRate API 테스트"""
    print("=" * 60)
    print("3. fundingRate API 테스트")
    print("=" * 60)
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for symbol in symbols:
        rate = get_funding_rate(symbol)
        print(f"✅ {symbol}: fundingRate = {rate:.6f} ({rate*100:.4f}%)")
    print()

def test_funding_fee():
    """펀딩비 계산 테스트"""
    print("=" * 60)
    print("4. 펀딩비 계산 테스트")
    print("=" * 60)
    
    position_value = 10000  # $10,000
    holding_hours = 24  # 24시간
    
    # API 조회
    fee_api = calculate_funding_fee(
        position_value=position_value,
        holding_hours=holding_hours,
        symbol="BTCUSDT",
        side="LONG",
        use_api=True
    )
    
    # 수동 지정
    fee_manual = calculate_funding_fee(
        position_value=position_value,
        holding_hours=holding_hours,
        funding_rate=0.0001,
        side="LONG",
        use_api=False
    )
    
    print(f"포지션 가치: ${position_value:,.0f}")
    print(f"보유 시간: {holding_hours}시간 (3회 정산)")
    print(f"펀딩비 (API): ${fee_api:.2f}")
    print(f"펀딩비 (수동 0.01%): ${fee_manual:.2f}")
    print()

if __name__ == "__main__":
    print("\n🚀 PR12 동적 반올림 및 펀딩 연동 테스트\n")
    
    try:
        test_exchange_info()
        test_round_tick()
        test_funding_rate()
        test_funding_fee()
        
        print("=" * 60)
        print("✅ 모든 테스트 완료!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
