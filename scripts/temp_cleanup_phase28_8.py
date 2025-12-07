#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-8: DB/Redis 상태 정리 스크립트
=====================================
이전 PHASE28-8 실행 데이터 정리
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger
from database import get_db_connection
import redis

logger = setup_logger("cleanup_phase28_8")


def cleanup_database():
    """DB에서 PHASE28-8 관련 데이터 정리"""
    logger.info("🧹 DB 정리 시작...")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. 기존 PHASE28-8 run_id 확인
                run_ids = [
                    'phase28_8_btc5m_baseline_v2_bull',
                    'phase28_8_btc5m_baseline_v2_bear',
                    'phase28_8_btc5m_baseline_v2_range'
                ]
                
                for run_id in run_ids:
                    # Trades 삭제 (trial_id 컬럼 사용)
                    cur.execute("DELETE FROM trading.trades WHERE trial_id = %s", (run_id,))
                    deleted_trades = cur.rowcount
                    
                    # Decisions 삭제
                    try:
                        cur.execute("DELETE FROM trading.decisions WHERE trial_id = %s", (run_id,))
                        deleted_decisions = cur.rowcount
                    except:
                        deleted_decisions = 0
                    
                    # Backtest runs 삭제 (있다면)
                    try:
                        cur.execute("DELETE FROM backtest.runs WHERE run_id = %s", (run_id,))
                        deleted_runs = cur.rowcount
                    except:
                        deleted_runs = 0
                    
                    if deleted_trades > 0 or deleted_decisions > 0 or deleted_runs > 0:
                        logger.info(f"🗑️ {run_id}: Trades={deleted_trades}, Decisions={deleted_decisions}, Runs={deleted_runs}")
                
                logger.info("✅ DB 정리 완료")
                return True
        
    except Exception as e:
        logger.error(f"❌ DB 정리 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def cleanup_redis():
    """Redis 상태 정리"""
    logger.info("🧹 Redis 정리 시작...")
    
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # 1. FlowGuardian 관련 키 정리
        patterns = [
            'cooldown:*',
            'budget:*',
            'position:*',
            'guardian:*',
            'phase28_8:*'
        ]
        
        total_deleted = 0
        for pattern in patterns:
            keys = r.keys(pattern)
            if keys:
                deleted = r.delete(*keys)
                total_deleted += deleted
                logger.info(f"🗑️ {pattern}: {deleted}개 키 삭제")
        
        logger.info(f"✅ Redis 정리 완료: 총 {total_deleted}개 키 삭제")
        return True
        
    except Exception as e:
        logger.error(f"❌ Redis 정리 실패: {e}")
        return False


def main():
    """메인 진입점"""
    print("=" * 80)
    print("🧹 PHASE28-8 DB/Redis 정리")
    print("=" * 80)
    print()
    
    # DB 정리
    db_ok = cleanup_database()
    
    # Redis 정리
    redis_ok = cleanup_redis()
    
    print()
    print("=" * 80)
    if db_ok and redis_ok:
        print("✅ 정리 완료: 백테스트 실행 준비됨")
    else:
        print("⚠️ 정리 중 일부 실패 (백테스트 실행은 가능할 수 있음)")
    print("=" * 80)
    
    return 0 if (db_ok and redis_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
