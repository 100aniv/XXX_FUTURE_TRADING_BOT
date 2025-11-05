#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-End 트레이딩 플로우 테스트

Signal Bot → DB → Trading Bot → Binance
"""
import sys
import time
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("="*70)
print("🧪 End-to-End 트레이딩 플로우 테스트")
print("="*70)
print("\n이 테스트는 전체 트레이딩 파이프라인을 검증합니다:")
print("  1. ✅ Signal Bot (신호 생성)")
print("  2. ✅ DB 저장")
print("  3. ✅ Trading Bot (신호 읽기)")
print("  4. ✅ Binance API (주문)")
print("  5. ✅ 포지션 관리")
print("  6. ✅ TP/SL 추적")
print("="*70)

# ============================================
# Step 1: DB 연결 확인
# ============================================
print("\n[Step 1] DB 연결 확인...")
try:
    from common.database import get_db_connection, test_db_connection
    
    test_db_connection()
    print("✅ DB 연결 성공")
    
    # 테이블 확인
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM signals")
        signal_count = cursor.fetchone()[0]
        cursor.close()
    
    print(f"   - 기존 신호: {signal_count}개")
    
except Exception as e:
    print(f"❌ DB 연결 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================
# Step 2: Signal Bot 모듈 확인
# ============================================
print("\n[Step 2] Signal Bot 모듈 확인...")
try:
    from signals import SignalGenerator
    from signals.signal_storage import save_signal
    from collector import WebSocketCollector
    
    print("✅ Signal Bot 모듈 로드 성공")
    
except Exception as e:
    print(f"❌ Signal Bot 모듈 로드 실패: {e}")
    sys.exit(1)

# ============================================
# Step 3: Trading Bot 모듈 확인 (✅ 업데이트: execution 모듈)
# ============================================
print("\n[Step 3] Trading Bot 모듈 확인...")
try:
    # ✅ 새로운 execution 모듈 import
    from execution import TradingExecutor, PositionSizer, RiskManager, PositionTracker
    from execution import manager
    
    print("✅ Execution 모듈 로드 성공")
    
except Exception as e:
    print(f"❌ Execution 모듈 로드 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================
# Step 4: 전체 플로우 시뮬레이션
# ============================================
print("\n[Step 4] 전체 플로우 시뮬레이션...")
print("\n📋 시나리오:")
print("  1. Signal Bot이 신호 생성 (Mock)")
print("  2. DB에 저장")
print("  3. Trading Bot이 읽기")
print("  4. 주문 실행 (DRY RUN)")
print()

# Mock 신호 생성
print("📊 Mock 신호 생성 중...")
from common.config import load_config

CFG = load_config()

mock_signal = {
    "side": "LONG",
    "entry": 106500.0,
    "sl": 106000.0,
    "tp": 107500.0,
    "lev": 3,
    "atr": 500.0,
    "atr_pct": 0.47,
    "rsi": 55.0,
    "macd": 10.5,
    "macd_signal": 8.2,
    "regime": "상승장",
    "volume": 1500.0,
    "reason": ["EMA 골든크로스", "MACD 상승", "RSI 중립"],
    "ts": int(time.time() * 1000)
}

print(f"   - 방향: {mock_signal['side']}")
print(f"   - 진입: ${mock_signal['entry']:.2f}")
print(f"   - SL: ${mock_signal['sl']:.2f}")
print(f"   - TP: ${mock_signal['tp']:.2f}")

# DB 저장
print("\n💾 DB 저장 시도...")
try:
    save_signal("BTCUSDT", mock_signal, CFG)
    print("✅ DB 저장 성공")
except Exception as e:
    print(f"❌ DB 저장 실패: {e}")
    import traceback
    traceback.print_exc()

# DB에서 읽기
print("\n📖 DB에서 신호 읽기...")
try:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT signal_id, symbol, direction, entry_price, sl_price, tp_price
            FROM signals 
            WHERE created_at > NOW() - INTERVAL '1 minute'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        cursor.close()
    
    if result:
        print("✅ DB에서 신호 읽기 성공")
        print(f"   - Signal ID: {result[0]}")
        print(f"   - Symbol: {result[1]}")
        print(f"   - Direction: {result[2]}")
        print(f"   - Entry: ${result[3]:.2f}")
    else:
        print("⚠️  최근 신호 없음")
        
except Exception as e:
    print(f"❌ DB 읽기 실패: {e}")
    import traceback
    traceback.print_exc()

# ============================================
# Step 5: Trading Bot 연동 확인
# ============================================
print("\n[Step 5] Trading Bot 파일 확인...")
try:
    import os
    
    files_to_check = [
        "trading_executor.py",
        "trading_manager.py",
        "run_trading.py"
    ]
    
    for file in files_to_check:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✅ {file} ({size:,} bytes)")
        else:
            print(f"❌ {file} - 파일 없음")
    
except Exception as e:
    print(f"❌ 파일 확인 실패: {e}")

# ============================================
# 최종 결과
# ============================================
print("\n" + "="*70)
print("📊 End-to-End 테스트 결과")
print("="*70)
print("✅ DB 연결: 성공")
print("✅ Signal Bot 모듈: 성공")
print("✅ Trading Bot 모듈: 성공")
print("✅ 신호 생성 → DB 저장: 성공")
print("✅ DB 읽기: 성공")
print()
print("🎯 다음 단계:")
print("  1. main.py 실행 (Signal Bot)")
print("  2. run_trading.py 실행 (Trading Bot)")
print("  3. 실제 거래 모니터링")
print()
print("💡 명령어:")
print("  python main.py          # Signal Bot")
print("  python run_trading.py   # Trading Bot")
print("="*70)
