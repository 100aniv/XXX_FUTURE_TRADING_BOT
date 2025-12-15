#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE35: Fast Gate Test Runner
===============================

기존 18/18 SSOT로 pytest 실행 + 결과 판정

Usage:
    python scripts/phase35/run_tests_fast_gate.py
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Project root 추가
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger("run_tests_fast_gate")


def run_fast_gate() -> int:
    """Fast Gate 테스트 실행"""
    logger.info("=" * 80)
    logger.info("PHASE35: Fast Gate Test")
    logger.info("=" * 80)
    logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # pytest 실행 (기존 18/18 SSOT)
        logger.info("🔄 Fast Gate 테스트 실행 중...")
        result = subprocess.run(
            ["pytest", "tests/", "-v", "--tb=short", "-x"],
            cwd=str(project_root),
            capture_output=False,
            timeout=300
        )
        
        if result.returncode == 0:
            logger.info("✅ Fast Gate: PASS (모든 테스트 통과)")
            return 0
        else:
            logger.error("❌ Fast Gate: FAIL (테스트 실패)")
            return 1
    
    except subprocess.TimeoutExpired:
        logger.error("❌ Fast Gate: TIMEOUT (300초 초과)")
        return 1
    except Exception as e:
        logger.error(f"❌ Fast Gate 실행 중 오류: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


def main():
    """메인 함수"""
    exit_code = run_fast_gate()
    
    logger.info("=" * 80)
    logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Exit Code: {exit_code}")
    logger.info("=" * 80)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
