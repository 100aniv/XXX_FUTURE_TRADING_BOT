#!/usr/bin/env python3
"""Collector WebSocket 실제 연결 테스트"""
import time
import signal
import sys

print("="*60)
print("🧪 Collector WebSocket 실제 연결 테스트")
print("="*60)
print("⚠️  Ctrl+C로 종료하세요 (10초 후 자동 종료)")
print("="*60)

from collector import WebSocketCollector

# 상태 추적
state = {
    "connected": False,
    "candles_received": 0,
    "start_time": time.time()
}

def on_candle(symbol, candle, is_closed, timeframe):
    state["candles_received"] += 1
    status = "🟢 CLOSED" if is_closed else "⚪ UPDATE"
    print(f"{status} | {symbol} {timeframe} | 종가: {candle['close']:.2f} | 거래량: {candle['volume']:.2f}")
    
    # 3개 받으면 성공
    if state["candles_received"] >= 3:
        print("\n✅ 3개 캔들 수신 완료! 테스트 성공!")
        collector.stop()
        sys.exit(0)

def on_connect():
    state["connected"] = True
    print("🔗 WebSocket 연결 성공!")

def on_error(e):
    print(f"💥 WebSocket 오류: {e}")

def on_close_reconnect():
    print("🔌 WebSocket 연결 끊김... 재연결 중...")

# Collector 시작
collector = WebSocketCollector(["BTCUSDT"], "1m")
collector.on_candle(on_candle)
collector.on_connect(on_connect)
collector.on_error(on_error)
collector.on_close_reconnect(on_close_reconnect)

# Ctrl+C 핸들러
def signal_handler(sig, frame):
    print(f"\n\n⏹ 종료 신호 수신")
    print(f"📊 통계:")
    print(f"   - 연결 성공: {'✅' if state['connected'] else '❌'}")
    print(f"   - 수신 캔들: {state['candles_received']}개")
    print(f"   - 실행 시간: {time.time() - state['start_time']:.1f}초")
    collector.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

print("\n🚀 WebSocket 연결 시작...\n")
collector.start()

# 10초 타임아웃
time.sleep(10)
print("\n⏱ 10초 타임아웃")
print(f"📊 통계:")
print(f"   - 연결 성공: {'✅' if state['connected'] else '❌'}")
print(f"   - 수신 캔들: {state['candles_received']}개")
collector.stop()
