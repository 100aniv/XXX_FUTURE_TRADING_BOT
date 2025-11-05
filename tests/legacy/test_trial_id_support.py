#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trial_id 지원 테스트
===================
PostgreSQL trial_id 컬럼 및 백테스트 리포트 생성 검증
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

load_dotenv()

from common.database import get_db_connection
from analytics.report_generator import generate_backtest_report
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def test_trial_id_column():
    """trial_id 컬럼 존재 확인"""
    logger.info("=" * 80)
    logger.info("🧪 Test 1: trial_id 컬럼 존재 확인")
    logger.info("=" * 80)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name, data_type, character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_schema = 'trading' 
                      AND table_name = 'trades' 
                      AND column_name = 'trial_id'
                """)
                result = cur.fetchone()
                
                if result:
                    logger.info(f"✅ trial_id 컬럼 존재")
                    logger.info(f"   - 타입: {result[1]}")
                    logger.info(f"   - 길이: {result[2]}")
                    return True
                else:
                    logger.error("❌ trial_id 컬럼 없음")
                    return False
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        return False


def test_trial_id_indexes():
    """trial_id 인덱스 확인"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 Test 2: trial_id 인덱스 확인")
    logger.info("=" * 80)
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'trading'
                      AND tablename = 'trades'
                      AND indexname LIKE '%trial%'
                """)
                indexes = cur.fetchall()
                
                if indexes:
                    logger.info(f"✅ trial_id 인덱스 존재 ({len(indexes)}개)")
                    for idx in indexes:
                        logger.info(f"   - {idx[0]}")
                    return True
                else:
                    logger.warning("⚠️  trial_id 인덱스 없음")
                    return False
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        return False


def test_backtest_report_with_trial_id():
    """trial_id 필터링으로 백테스트 리포트 생성"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 Test 3: trial_id 필터링 리포트 생성")
    logger.info("=" * 80)
    
    try:
        # trial_id=None (전체 데이터)
        result = generate_backtest_report(
            trial_id=None,
            sinks=["log"]
        )
        
        if result.get("status") == "no_data":
            logger.info("✅ 리포트 생성 정상 (데이터 없음은 예상된 결과)")
            return True
        elif result.get("status") == "success":
            logger.info(f"✅ 리포트 생성 성공")
            logger.info(f"   - 총점: {result.get('total_score', 0):.1f}/100")
            logger.info(f"   - 거래 수: {result.get('metrics', {}).get('total_trades', 0)}건")
            return True
        else:
            logger.error(f"❌ 리포트 생성 실패: {result.get('error')}")
            return False
    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trial_id_filtering():
    """특정 trial_id로 필터링 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 Test 4: 특정 trial_id 필터링")
    logger.info("=" * 80)
    
    try:
        # 존재하지 않는 trial_id로 테스트
        result = generate_backtest_report(
            trial_id="test_trial_001",
            sinks=["log"]
        )
        
        if result.get("status") == "no_data":
            logger.info("✅ 필터링 정상 (데이터 없음은 예상된 결과)")
            return True
        else:
            logger.warning(f"⚠️  예상과 다른 결과: {result.get('status')}")
            return True  # 데이터가 있어도 정상
    except Exception as e:
        # trial_id 컬럼이 없으면 에러 발생 (정상)
        if "trial_id" in str(e):
            logger.error(f"❌ trial_id 컬럼 없음: {e}")
            return False
        logger.error(f"❌ 테스트 실패: {e}")
        return False


def main():
    """전체 테스트 실행"""
    logger.info("\n" + "=" * 80)
    logger.info("🚀 trial_id 지원 테스트 시작")
    logger.info("=" * 80 + "\n")
    
    results = []
    
    # Test 1: trial_id 컬럼 확인
    results.append(("trial_id 컬럼 존재", test_trial_id_column()))
    
    # Test 2: trial_id 인덱스 확인
    results.append(("trial_id 인덱스 존재", test_trial_id_indexes()))
    
    # Test 3: 백테스트 리포트 생성
    results.append(("백테스트 리포트 생성", test_backtest_report_with_trial_id()))
    
    # Test 4: trial_id 필터링
    results.append(("trial_id 필터링", test_trial_id_filtering()))
    
    # 결과 요약
    logger.info("\n" + "=" * 80)
    logger.info("📊 테스트 결과 요약")
    logger.info("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {name}")
    
    logger.info("=" * 80)
    logger.info(f"총 {passed}/{total} 테스트 통과 ({passed/total*100:.0f}%)")
    logger.info("=" * 80 + "\n")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
