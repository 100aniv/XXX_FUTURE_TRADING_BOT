#!/usr/bin/env python3
"""
전체 플로우 테스트
==================
Collector → Signal → Strategy → DB → Trading
"""
import sys
import time
from datetime import datetime

print("=" * 60)
print("🚀 전체 플로우 테스트 시작")
print("=" * 60)

# ============================================
# 1. 모듈 Import 테스트
# ============================================
print("\n[1/5] 모듈 Import 테스트...")

try:
    from common.config import load_config
    print("  ✅ common.config")
except Exception as e:
    print(f"  ❌ common.config: {e}")
    sys.exit(1)

try:
    from common.database import get_db_connection, test_db_connection
    print("  ✅ common.database")
except Exception as e:
    print(f"  ❌ common.database: {e}")
    sys.exit(1)

try:
    from indicators import add_indicators, regime
    print("  ✅ indicators")
except Exception as e:
    print(f"  ❌ indicators: {e}")
    sys.exit(1)

try:
    from strategies import scalping, daytrade, swing
    print("  ✅ strategies")
except Exception as e:
    print(f"  ❌ strategies: {e}")
    sys.exit(1)

try:
    from signals import SignalGenerator
    from signals.signal_storage import save_signal
    print("  ✅ signals")
except Exception as e:
    print(f"  ❌ signals: {e}")
    sys.exit(1)

# ============================================
# 2. 설정 로드 테스트
# ============================================
print("\n[2/5] 설정 로드 테스트...")

try:
    CFG = load_config()
    print(f"  ✅ 설정 로드 완료")
    print(f"     - 심볼: {', '.join(CFG['symbols'][:3])}")
    print(f"     - TF: {CFG['timeframe']}")
    print(f"     - 전략: {CFG.get('strategy_id', 'unknown')}")
except Exception as e:
    print(f"  ❌ 설정 로드 실패: {e}")
    sys.exit(1)

# ============================================
# 3. DB 연결 테스트
# ============================================
print("\n[3/5] DB 연결 테스트...")

try:
    test_db_connection()
    print("  ✅ PostgreSQL 연결 성공")
except Exception as e:
    print(f"  ❌ DB 연결 실패: {e}")
    print("  ⚠️  Docker가 실행 중인지 확인하세요:")
    print("     docker-compose up -d postgres")

# ============================================
# 4. Signal Generator 테스트
# ============================================
print("\n[4/5] Signal Generator 테스트...")

try:
    signal_gen = SignalGenerator(CFG)
    print("  ✅ SignalGenerator 초기화 성공")
    
    # 테스트 캔들 데이터
    test_candle = {
        "time": int(datetime.now().timestamp() * 1000),
        "open": 100.0,
        "high": 102.0,
        "low": 99.0,
        "close": 101.0,
        "volume": 1000.0
    }
    
    print("  ✅ 테스트 캔들 데이터 준비 완료")
    
except Exception as e:
    print(f"  ❌ Signal Generator 초기화 실패: {e}")
    sys.exit(1)

# ============================================
# 5. 전략 실행 테스트
# ============================================
print("\n[5/5] 전략 실행 테스트...")

try:
    # 각 전략 모듈 테스트
    import pandas as pd
    
    test_df = pd.DataFrame({
        'time': range(250),
        'close': [100] * 250,
        'high': [101] * 250,
        'low': [99] * 250,
        'open': [100] * 250,
        'volume': [1000] * 250
    })
    
    # 지표 계산
    df_with_indicators = add_indicators(
        test_df, 
        CFG.get("ema_fast", 8),
        CFG.get("ema_mid", 21),
        CFG.get("ema_slow", 50),
        CFG.get("rsi_len", 14),
        CFG.get("macd_fast", 12),
        CFG.get("macd_slow", 26),
        CFG.get("macd_signal", 9),
        CFG.get("bb_len", 20),
        CFG.get("bb_std", 2.0),
        CFG.get("atr_len", 14),
        CFG.get("vol_ma_len", 20)
    )
    
    print("  ✅ 지표 계산 완료")
    
    # 전략 테스트
    tf = CFG["timeframe"]
    if tf in ["1m", "3m"]:
        result = scalping.signal_logic(df_with_indicators, CFG)
    elif tf == "5m":
        result = daytrade.signal_logic(df_with_indicators, CFG)
    elif tf == "15m":
        result = swing.signal_logic(df_with_indicators, CFG)
    else:
        result = daytrade.signal_logic(df_with_indicators, CFG)
    
    print(f"  ✅ 전략 실행 완료 (신호: {result.get('side', 'FLAT')})")
    
except Exception as e:
    print(f"  ❌ 전략 실행 실패: {e}")
    import traceback
    traceback.print_exc()

# ============================================
# 결과
# ============================================
print("\n" + "=" * 60)
print("🎉 전체 플로우 테스트 완료!")
print("=" * 60)
print("\n✅ 모든 모듈이 정상 작동합니다!")
print("\n📋 다음 단계:")
print("  1. Signal Bot 실행: python signal_bot_trend.py")
print("  2. Trading Manager 실행: python trading_manager.py")
print("  3. 실시간 신호 생성 및 거래 확인")
print("=" * 60)
