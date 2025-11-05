#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ensemble Module Test
====================
앙상블 모듈 단독 테스트
"""
import sys
from dotenv import load_dotenv

load_dotenv()

from common.logger import setup_logger
from common.database import get_db_connection, test_db_connection
from strategies import ensemble

logger = setup_logger(__name__, log_type="test")

def test_ensemble():
    """앙상블 모듈 테스트"""
    
    logger.info("="*60)
    logger.info("앙상블 모듈 테스트 시작")
    logger.info("="*60)
    
    # 1. DB 연결 테스트
    logger.info("\n[1/5] DB 연결 테스트...")
    test_db_connection()
    logger.info("✅ DB 연결 성공")
    
    # 2. CFG 확인
    logger.info("\n[2/5] CFG 설정 확인...")
    logger.info(f"  - weight_trend: {ensemble.CFG['weight_trend']}")
    logger.info(f"  - weight_reversion: {ensemble.CFG['weight_reversion']}")
    logger.info(f"  - weight_breakout: {ensemble.CFG['weight_breakout']}")
    logger.info(f"  - weight_scalping: {ensemble.CFG['weight_scalping']}")
    logger.info(f"  - weight_daytrade: {ensemble.CFG['weight_daytrade']}")
    logger.info(f"  - weight_swing: {ensemble.CFG['weight_swing']}")
    logger.info(f"  - alpha_winrate: {ensemble.CFG['alpha_winrate']}")
    logger.info(f"  - beta_rr: {ensemble.CFG['beta_rr']}")
    logger.info("✅ CFG 설정 확인 완료")
    
    # 3. 성과 메트릭 로드 테스트
    logger.info("\n[3/5] 성과 메트릭 로드 테스트...")
    try:
        with get_db_connection() as conn:
            perf = ensemble.load_strategy_performance(conn)
            logger.info(f"  로드된 전략: {list(perf.keys())}")
            for strategy_id, metrics in perf.items():
                logger.info(f"  - {strategy_id}: winrate={metrics['winrate']:.2f}, "
                          f"rr_mean={metrics['rr_mean']:.2f}, "
                          f"total_trades={metrics['total_trades']}")
        logger.info("✅ 성과 메트릭 로드 성공")
    except Exception as e:
        logger.error(f"❌ 성과 메트릭 로드 실패: {e}")
        return False
    
    # 4. 신호 조회 테스트
    logger.info("\n[4/5] 최근 신호 조회 테스트...")
    try:
        with get_db_connection() as conn:
            # 최근 신호 확인
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as cnt, 
                           MIN(created_at) as oldest, 
                           MAX(created_at) as newest
                    FROM monitoring.signals
                    WHERE created_at >= NOW() - INTERVAL '10 minutes'
                """)
                row = cur.fetchone()
                logger.info(f"  최근 10분 신호: {row[0]}개")
                if row[0] > 0:
                    logger.info(f"  범위: {row[1]} ~ {row[2]}")
                
            # 미처리 신호 확인
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as cnt
                    FROM monitoring.signals s
                    WHERE s.created_at >= NOW() - INTERVAL '10 minutes'
                      AND NOT EXISTS (
                          SELECT 1 FROM trading.decisions d
                          WHERE d.symbol = s.symbol
                            AND d.timeframe = s.timeframe
                            AND d.candle_closed_at = s.candle_closed_at
                      )
                """)
                cnt = cur.fetchone()[0]
                logger.info(f"  미처리 신호: {cnt}개")
        
        logger.info("✅ 신호 조회 성공")
    except Exception as e:
        logger.error(f"❌ 신호 조회 실패: {e}")
        return False
    
    # 5. 앙상블 처리 실행
    logger.info("\n[5/5] 앙상블 처리 실행...")
    try:
        with get_db_connection() as conn:
            ensemble.process_pending_signals(conn, logger=logger)
        logger.info("✅ 앙상블 처리 완료")
    except Exception as e:
        logger.error(f"❌ 앙상블 처리 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. 결과 확인
    logger.info("\n[6/6] 처리 결과 확인...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) as cnt,
                           MIN(created_at) as oldest,
                           MAX(created_at) as newest
                    FROM trading.decisions
                    WHERE created_at >= NOW() - INTERVAL '10 minutes'
                """)
                row = cur.fetchone()
                logger.info(f"  최근 10분 결정: {row[0]}개")
                if row[0] > 0:
                    logger.info(f"  범위: {row[1]} ~ {row[2]}")
                
                # 최근 결정 상세
                cur.execute("""
                    SELECT symbol, timeframe, chosen_side, score, 
                           array_length(from_signals, 1) as signal_count,
                           created_at
                    FROM trading.decisions
                    WHERE created_at >= NOW() - INTERVAL '10 minutes'
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                rows = cur.fetchall()
                if rows:
                    logger.info("  최근 결정:")
                    for row in rows:
                        logger.info(f"    - {row[0]} {row[1]}: {row[2]} (score={row[3]:.3f}, signals={row[4]})")
        
        logger.info("✅ 결과 확인 완료")
    except Exception as e:
        logger.error(f"❌ 결과 확인 실패: {e}")
        return False
    
    logger.info("\n" + "="*60)
    logger.info("✅ 모든 테스트 통과!")
    logger.info("="*60)
    return True

if __name__ == "__main__":
    try:
        success = test_ensemble()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n테스트 중단")
        sys.exit(1)
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
