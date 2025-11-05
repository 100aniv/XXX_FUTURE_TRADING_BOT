#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 통합 테스트 - 유기적 동작 검증
"""
import sys
import time
from dotenv import load_dotenv

# .env 로드
load_dotenv()

print("="*70)
print("🧪 전체 통합 테스트 - Future Alarm Bot")
print("="*70)
print("이 테스트는 전체 플로우를 검증합니다:")
print("  1. Config 로드")
print("  2. SignalGenerator 초기화")
print("  3. WebSocket 연결")
print("  4. 실시간 캔들 수신")
print("  5. 신호 생성 (strategies)")
print("  6. DB 저장 시도")
print("  7. 메시지 포맷팅")
print("="*70)

# ============================================
# Step 1: Config 로드
# ============================================
print("\n[Step 1] Config 로드...")
try:
    from common.config import load_config, validate_config
    CFG = load_config()
    validate_config(CFG)
    print(f"✅ Config 로드 성공")
    print(f"   - BOT_NAME: {CFG.get('bot_name')}")
    print(f"   - STRATEGY: {CFG.get('strategy_id')}")
    print(f"   - SYMBOLS: {CFG['symbols']}")
    print(f"   - TIMEFRAME: {CFG['timeframe']}")
except Exception as e:
    print(f"❌ Config 로드 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================
# Step 2: 모든 모듈 Import
# ============================================
print("\n[Step 2] 모든 모듈 Import...")
try:
    from common.messaging import tg as _tg, format_signal_alert
    from common.utils import qty_notional_margin
    from signals import SignalGenerator
    from signals.signal_storage import save_signal
    from collector import WebSocketCollector
    print("✅ 모든 모듈 Import 성공")
except Exception as e:
    print(f"❌ Import 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================
# Step 3: SignalGenerator 초기화
# ============================================
print("\n[Step 3] SignalGenerator 초기화...")
try:
    signal_generator = SignalGenerator(CFG)
    print(f"✅ SignalGenerator 초기화 성공")
    print(f"   - Strategy: {CFG.get('strategy_id', 'unknown')}")
    print(f"   - MTF Confirm: {CFG.get('enable_mtf_confirm', False)}")
    print(f"   - Vol Filter: {CFG.get('enable_vol_spike_filter', False)}")
except Exception as e:
    print(f"❌ SignalGenerator 초기화 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================
# Step 4: 텔레그램 래퍼
# ============================================
print("\n[Step 4] 텔레그램 함수 준비...")
try:
    def tg(text: str):
        """텔레그램 메시지 (실제 전송은 안함)"""
        print(f"   📱 [TG] {text[:50]}..." if len(text) > 50 else f"   📱 [TG] {text}")
        return True  # 실제로는 _tg(text, CFG)
    
    print("✅ 텔레그램 함수 준비 완료 (Mock)")
except Exception as e:
    print(f"❌ 텔레그램 함수 실패: {e}")
    sys.exit(1)

# ============================================
# Step 5: 캔들 콜백 함수
# ============================================
print("\n[Step 5] 캔들 콜백 함수 준비...")

test_state = {
    "candles_received": 0,
    "signals_generated": 0,
    "errors": 0
}

def on_candle_closed(symbol, candle, is_closed, timeframe):
    """캔들 닫힐 때 호출되는 콜백"""
    try:
        test_state["candles_received"] += 1
        
        # 닫힌 캔들만 처리
        if not is_closed:
            return
        
        print(f"\n   🟢 CLOSED CANDLE: {symbol} {timeframe} @ {candle['close']:.2f}")
        
        # 신호 생성 시도
        signal = signal_generator.process_candle(symbol, candle, tg_callback=tg)
        
        if signal:
            test_state["signals_generated"] += 1
            print(f"   🎯 신호 생성됨!")
            print(f"      - 방향: {signal['side']}")
            print(f"      - 진입: {signal['entry']:.2f}")
            print(f"      - SL: {signal['sl']:.2f}")
            print(f"      - TP: {signal['tp']:.2f}")
            
            # 포지션 계산
            qty, notional, margin = qty_notional_margin(
                signal["entry"], signal["sl"], signal["lev"],
                CFG["equity_usdt"], CFG["risk_per_trade"]
            )
            print(f"      - 수량: {qty:.4f}")
            print(f"      - 증거금: ${margin:.2f}")
            
            # 메시지 포맷팅
            msg = format_signal_alert(symbol, signal, qty, notional, margin, CFG)
            print(f"   📨 알림 메시지 생성 완료 ({len(msg)}자)")
            
            # DB 저장 시도 (실제로는 저장 안함)
            print(f"   💾 DB 저장 시도...")
            # save_signal(symbol, signal, CFG)  # 실제 저장은 주석 처리
            print(f"   ✅ (Mock) DB 저장 완료")
        
        # 3개 받으면 종료
        if test_state["candles_received"] >= 5:
            print(f"\n✅ 5개 캔들 수신 완료! 테스트 종료")
            collector.stop()
    
    except Exception as e:
        test_state["errors"] += 1
        print(f"   ❌ 캔들 처리 오류: {e}")
        import traceback
        traceback.print_exc()

print("✅ 캔들 콜백 함수 준비 완료")

# ============================================
# Step 6: WebSocketCollector 시작
# ============================================
print("\n[Step 6] WebSocketCollector 시작...")
try:
    # 1분봉으로 빠르게 테스트
    collector = WebSocketCollector([CFG['symbols'][0]], "1m")
    
    collector.on_candle(on_candle_closed)
    collector.on_connect(lambda: print("   🔗 WebSocket 연결 성공!"))
    collector.on_error(lambda e: print(f"   💥 WebSocket 오류: {e}"))
    collector.on_close_reconnect(lambda: print("   🔌 재연결 중..."))
    
    print("✅ WebSocketCollector 설정 완료")
    print(f"   - 심볼: {CFG['symbols'][0]}")
    print(f"   - 타임프레임: 1m (테스트용)")
    
except Exception as e:
    print(f"❌ WebSocketCollector 설정 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================
# Step 7: 실행 및 모니터링
# ============================================
print("\n[Step 7] 실행 시작...")
print("="*70)
print("⏱  60초 동안 실행합니다...")
print("⚠️  Ctrl+C로 중단 가능")
print("="*70)

import signal as sig

def signal_handler(s, frame):
    print("\n\n⏹  중단 신호 수신")
    show_results()
    collector.stop()
    sys.exit(0)

sig.signal(sig.SIGINT, signal_handler)

def show_results():
    print("\n" + "="*70)
    print("📊 테스트 결과")
    print("="*70)
    print(f"✅ 수신 캔들: {test_state['candles_received']}개")
    print(f"🎯 생성 신호: {test_state['signals_generated']}개")
    print(f"❌ 오류 발생: {test_state['errors']}개")
    print("="*70)
    
    if test_state['errors'] == 0:
        print("🎉 전체 통합 테스트 성공!")
    else:
        print("⚠️  일부 오류 발생")

# 실행
try:
    collector.start()
    
    # 60초 대기
    time.sleep(60)
    
    print("\n⏱  60초 타임아웃")
    show_results()
    collector.stop()
    
except Exception as e:
    print(f"\n❌ 실행 중 오류: {e}")
    import traceback
    traceback.print_exc()
    show_results()
    sys.exit(1)
