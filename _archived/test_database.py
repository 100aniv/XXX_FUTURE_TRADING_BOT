#!/usr/bin/env python3
"""common.database 모듈 테스트"""

from common.database import (
    get_db_connection, 
    save_signal_to_db, 
    test_db_connection,
    get_latest_signals
)
from datetime import datetime

# 1. DB 연결 테스트
print("=" * 60)
print("1. DB 연결 테스트")
print("=" * 60)
test_db_connection()

# 2. 신호 저장 테스트
print("\n" + "=" * 60)
print("2. 신호 저장 테스트")
print("=" * 60)

success = save_signal_to_db(
    signal_id="test-001",
    strategy_id="scalping",
    bot_id="test-bot",
    symbol="BTCUSDT",
    timeframe="1m",
    candle_closed_at=datetime.now(),
    direction="LONG",
    confidence=0.85,
    entry_price=100000,
    sl_price=99500,
    tp_price=101000,
    atr=500,
    leverage=10,
    features={"test": True}
)
print(f"저장 결과: {'성공' if success else '실패 또는 중복'}")

# 3. 신호 조회 테스트
print("\n" + "=" * 60)
print("3. 최근 신호 조회")
print("=" * 60)

signals = get_latest_signals(strategy_id="scalping", limit=3)
for sig in signals:
    print(f"  - {sig['symbol']} {sig['direction']} @ {sig['entry_price']}")

print("\n✅ 모든 테스트 완료!")
