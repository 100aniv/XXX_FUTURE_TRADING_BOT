#!/usr/bin/env python3
"""common.logger 모듈 테스트"""

from common.logger import setup_logger

# 로거 생성
logger = setup_logger(__name__)

# 테스트 로깅
logger.info("✅ common.logger 모듈 테스트 성공!")
logger.debug("디버그 메시지")
logger.warning("⚠️  경고 메시지")
logger.error("❌ 에러 메시지")

print("\n✅ 모든 로깅 레벨 테스트 완료!")
