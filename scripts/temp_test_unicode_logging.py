#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-8: Unicode 로깅 테스트
================================
한글, 이모지, 복합 문자열이 정상적으로 로그에 기록되는지 검증
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("unicode_test", log_type="application")

def test_unicode_logging():
    """Unicode 문자열 로깅 테스트"""
    
    print("=" * 80)
    print("🧪 Unicode 로깅 테스트 시작")
    print("=" * 80)
    
    # 1. 기본 한글
    logger.info("✅ 한글 로깅 테스트: 안녕하세요")
    
    # 2. 이모지
    logger.info("🚀 이모지 테스트: 🎯 📊 💰 ⚠️ ❌ ✅")
    
    # 3. 복합 문자열
    logger.info("📈 PHASE28-8: Multi-Period Baseline Validation 시작")
    logger.info("📊 Bull 구간 백테스트: 2024-10-01 ~ 2024-10-31")
    logger.info("💹 Sharpe Ratio: +1.234, Win Rate: 45.6%")
    
    # 4. 경고 및 에러 메시지
    logger.warning("⚠️ 경고: Unicode 테스트 중입니다")
    logger.error("❌ 에러: 이것은 테스트 에러 메시지입니다 (실제 에러 아님)")
    
    # 5. 긴 복합 메시지
    logger.info("""
    ========================================
    🎯 PHASE28-8 목표 메트릭
    ========================================
    - Trade Count: ≥ 20 per month
    - Sharpe Ratio: ≥ 0.0 (모든 Period)
    - Win Rate: ≥ 40%
    - Max Drawdown: ≤ 20%
    ========================================
    """)
    
    print("\n" + "=" * 80)
    print("✅ Unicode 로깅 테스트 완료")
    print("=" * 80)
    print("\n📁 로그 파일 확인:")
    print("   - logs/application/[today].log")
    print("   - logs/application.log")
    print("\n💡 위 로그 파일에서 한글/이모지가 깨지지 않았는지 확인하세요.")
    
    return True

if __name__ == "__main__":
    try:
        test_unicode_logging()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unicode 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
