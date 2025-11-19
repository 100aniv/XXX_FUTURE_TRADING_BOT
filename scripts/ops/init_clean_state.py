#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE18-1: 실행 전 환경 초기화 스크립트
==========================================
실행 간 상태 간섭 방지를 위한 clean-state 보장

Usage:
    # 전체 초기화 (Redis + 로그)
    python scripts/ops/init_clean_state.py

    # Redis만 초기화
    python scripts/ops/init_clean_state.py --redis-only

    # DB도 초기화 (run_id 지정)
    python scripts/ops/init_clean_state.py --db --run-id XXX

    # 로그만 백업
    python scripts/ops/init_clean_state.py --logs-only
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
import shutil

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def init_redis(verbose: bool = True) -> bool:
    """
    Redis 초기화 (Guard/Cooldown/Dedup 키 삭제)
    
    Args:
        verbose: 상세 로그 출력 여부
    
    Returns:
        bool: 성공 여부
    """
    try:
        import redis
        
        # Redis 연결
        client = redis.Redis(
            host='localhost',
            port=6379,
            decode_responses=True,
            socket_connect_timeout=5
        )
        
        # 연결 테스트
        client.ping()
        
        if verbose:
            logger.info("=" * 60)
            logger.info("🔧 REDIS 초기화 시작")
            logger.info("=" * 60)
        
        # 초기화 전 키 개수 확인
        patterns = ['candle:seen:*', 'flow_guard:*', 'cooldown:*', 'signal:*']
        total_deleted = 0
        
        for pattern in patterns:
            keys = client.keys(pattern)
            if keys:
                deleted = client.delete(*keys)
                total_deleted += deleted
                if verbose:
                    logger.info(f"  ✅ 삭제: {pattern} → {deleted}개 키")
            else:
                if verbose:
                    logger.info(f"  ⚪ 없음: {pattern}")
        
        if verbose:
            logger.info("-" * 60)
            logger.info(f"✅ Redis 초기화 완료: 총 {total_deleted}개 키 삭제")
            logger.info("=" * 60)
        
        return True
        
    except ImportError:
        logger.warning("⚠️ redis 패키지 없음 - Redis 초기화 건너뜀")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Redis 연결 실패: {e} - 초기화 건너뜀")
        return False


def init_db(run_id: str, verbose: bool = True) -> bool:
    """
    DB 초기화 (run_id 기반 포지션/트레이드 삭제)
    
    Args:
        run_id: 삭제할 run_id
        verbose: 상세 로그 출력 여부
    
    Returns:
        bool: 성공 여부
    """
    if not run_id:
        logger.warning("⚠️ run_id 미지정 - DB 초기화 건너뜀")
        return False
    
    try:
        from database.postgres import get_db_connection
        
        if verbose:
            logger.info("=" * 60)
            logger.info(f"🔧 DB 초기화 시작 (run_id: {run_id})")
            logger.info("=" * 60)
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # positions 삭제
                cur.execute(
                    "DELETE FROM positions WHERE run_id = %s",
                    (run_id,)
                )
                positions_deleted = cur.rowcount
                
                # trades 삭제
                cur.execute(
                    "DELETE FROM trades WHERE run_id = %s",
                    (run_id,)
                )
                trades_deleted = cur.rowcount
                
                if verbose:
                    logger.info(f"  ✅ positions 삭제: {positions_deleted}개")
                    logger.info(f"  ✅ trades 삭제: {trades_deleted}개")
        
        if verbose:
            logger.info("-" * 60)
            logger.info(f"✅ DB 초기화 완료 (run_id: {run_id})")
            logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ DB 초기화 실패: {e}")
        return False


def backup_logs(verbose: bool = True) -> bool:
    """
    로그 파일 백업 (타임스탬프 백업)
    
    Args:
        verbose: 상세 로그 출력 여부
    
    Returns:
        bool: 성공 여부
    """
    try:
        logs_dir = project_root / "logs"
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True)
            if verbose:
                logger.info("📁 logs 디렉토리 생성")
            return True
        
        if verbose:
            logger.info("=" * 60)
            logger.info("🔧 로그 백업 시작")
            logger.info("=" * 60)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_files = ['application.log', 'trading.log']
        backed_up = 0
        
        for log_file in log_files:
            log_path = logs_dir / log_file
            if log_path.exists() and log_path.stat().st_size > 0:
                # 백업
                backup_name = f"{log_file}.{timestamp}.bak"
                backup_path = logs_dir / backup_name
                shutil.copy2(log_path, backup_path)
                
                backed_up += 1
                if verbose:
                    logger.info(f"  ✅ 백업: {log_file} → {backup_name}")
            else:
                if verbose:
                    logger.info(f"  ⚪ 없음 또는 빈 파일: {log_file}")
        
        # 로그 백업 완료 후, 원본 파일 초기화 (logger가 다시 쓰지 못하도록 나중에 수행)
        # Note: logger.info() 호출 후에 파일을 초기화해야 로그가 남지 않음
        
        if verbose:
            logger.info("-" * 60)
            logger.info(f"✅ 로그 백업 완료: {backed_up}개 파일")
            logger.info("=" * 60)
        
        # ⚠️ 여기서 로그 파일 초기화 (logger.info 완료 후)
        # 단, 이 스크립트 자체가 로그를 쓰고 있으므로, 완전 초기화는 불가능
        # 실제 초기화는 run_paper/run_backtest 시작 전에 수행되어야 함
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 로그 백업 실패: {e}")
        return False


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description='PHASE18-1: 실행 전 환경 초기화',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--redis-only',
        action='store_true',
        default=False,
        help='Redis만 초기화'
    )
    
    parser.add_argument(
        '--logs-only',
        action='store_true',
        default=False,
        help='로그만 백업'
    )
    
    parser.add_argument(
        '--db',
        action='store_true',
        default=False,
        help='DB도 초기화 (--run-id 필수)'
    )
    
    parser.add_argument(
        '--run-id',
        type=str,
        default=None,
        help='DB 초기화 시 대상 run_id'
    )
    
    parser.add_argument(
        '--quiet',
        action='store_true',
        default=False,
        help='최소 로그 출력'
    )
    
    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_args()
    verbose = not args.quiet
    
    if verbose:
        logger.info("")
        logger.info("=" * 60)
        logger.info("🚀 PHASE18-1: Clean-State 초기화")
        logger.info("=" * 60)
        logger.info("")
    
    success = True
    
    # Redis 초기화
    if not args.logs_only:
        redis_ok = init_redis(verbose=verbose)
        if not redis_ok:
            logger.warning("⚠️ Redis 초기화 실패 (계속 진행)")
    
    # DB 초기화 (optional)
    if args.db:
        if args.run_id:
            db_ok = init_db(args.run_id, verbose=verbose)
            if not db_ok:
                logger.warning("⚠️ DB 초기화 실패 (계속 진행)")
        else:
            logger.warning("⚠️ --run-id 미지정 - DB 초기화 건너뜀")
    
    # 로그 백업
    if not args.redis_only:
        logs_ok = backup_logs(verbose=verbose)
        if not logs_ok:
            logger.warning("⚠️ 로그 백업 실패 (계속 진행)")
    
    if verbose:
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Clean-State 초기화 완료")
        logger.info("=" * 60)
        logger.info("")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
