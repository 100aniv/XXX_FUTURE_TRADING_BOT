#!/usr/bin/env python3
"""Collector 빠른 테스트"""
print("="*50)
print("🧪 Collector 모듈 테스트")
print("="*50)

# Test 1: Import
print("\n[1] Import 테스트...")
try:
    from collector import WebSocketCollector, bootstrap_history
    print("✅ Import 성공")
except Exception as e:
    print(f"❌ Import 실패: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 2: 초기화
print("\n[2] WebSocketCollector 초기화...")
try:
    collector = WebSocketCollector(["BTCUSDT"], "1m")
    print(f"✅ 초기화 성공")
    print(f"   - 심볼: {collector.symbols}")
    print(f"   - 타임프레임: {collector.timeframe}")
except Exception as e:
    print(f"❌ 초기화 실패: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 3: 콜백 등록
print("\n[3] 콜백 등록...")
try:
    def test_callback(symbol, candle, is_closed, timeframe):
        pass
    
    collector.on_candle(test_callback)
    collector.on_connect(lambda: None)
    collector.on_error(lambda e: None)
    print("✅ 콜백 등록 성공")
except Exception as e:
    print(f"❌ 콜백 등록 실패: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*50)
print("✅ 모든 기본 테스트 통과!")
print("="*50)
