#!/usr/bin/env python3
"""새로운 로깅 시스템 테스트"""

from common.logger import setup_logger

# 1. 신호 봇 로그
signal_logger = setup_logger("signal_bot_test", log_type="signals")
signal_logger.info("✅ 신호 생성: BTCUSDT LONG @ 100000")
signal_logger.warning("⚠️  신호 품질 낮음: confidence 0.6")

# 2. 거래 봇 로그
trading_logger = setup_logger("trading_manager_test", log_type="trading")
trading_logger.info("📊 거래 실행: BTCUSDT LONG x1.5")
trading_logger.error("❌ 거래 실패: 잔고 부족")

# 3. 일반 로그
app_logger = setup_logger("application_test", log_type="application")
app_logger.info("🚀 시스템 시작")
app_logger.debug("디버그 메시지")

print("\n" + "="*60)
print("✅ 로깅 테스트 완료!")
print("="*60)
print("\n📁 생성된 로그 파일 확인:")
print("  logs/signals/2025-10-18.log")
print("  logs/trading/2025-10-18.log")
print("  logs/errors/2025-10-18.log (에러만)")
print("  logs/application.log (전체 통합)")
