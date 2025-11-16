#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE16 Paper Trading Status Checker
=====================================
Paper trading 상태 확인 (Read-only)

Usage:
    python scripts/check_paper.py
"""
import sys
from pathlib import Path
from datetime import datetime
import yaml

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def check_redis():
    """Redis 연결 확인"""
    try:
        import redis
        from common.config_loader import load_config_with_mode
        
        cfg = load_config_with_mode(mode="paper")
        redis_config = cfg.get("monitoring", {}).get("redis", {})
        
        # 환경변수 처리 (${REDIS_HOST} → localhost)
        redis_host = redis_config.get("host", "localhost")
        redis_port = redis_config.get("port", 6379)
        
        # 환경변수 형식이면 기본값 사용
        if isinstance(redis_host, str) and redis_host.startswith("${"):
            redis_host = "localhost"
        if isinstance(redis_port, str) and redis_port.startswith("${"):
            redis_port = 6379
        
        client = redis.Redis(
            host=redis_host,
            port=int(redis_port),
            db=redis_config.get("db", 0),
            decode_responses=True
        )
        
        client.ping()
        logger.info(f"✅ Redis 연결 성공: {redis_config.get('host')}:{redis_config.get('port')}")
        
        # 활성 키 개수 확인
        dedup_keys = len(client.keys("dedup:*"))
        cooldown_keys = len(client.keys("cooldown:*"))
        signal_keys = len(client.keys("signal:*"))
        
        logger.info(f"📊 Redis 키 현황:")
        logger.info(f"   Dedup: {dedup_keys}개")
        logger.info(f"   Cooldown: {cooldown_keys}개")
        logger.info(f"   Signal: {signal_keys}개")
        
        return True
    except Exception as e:
        logger.error(f"❌ Redis 연결 실패: {e}")
        return False


def check_recent_runs():
    """최근 Paper run 확인"""
    scorecard_dir = Path("scorecards/paper_phase16")
    
    if not scorecard_dir.exists():
        logger.warning("⚠️ scorecards/paper_phase16 디렉토리가 없습니다")
        return
    
    runs = sorted([d for d in scorecard_dir.iterdir() if d.is_dir()], reverse=True)
    
    if not runs:
        logger.warning("⚠️ Paper trading run이 없습니다")
        return
    
    logger.info(f"\n📁 최근 Paper Trading Runs ({len(runs)}개):")
    logger.info("=" * 70)
    
    for i, run_dir in enumerate(runs[:5], 1):
        run_id = run_dir.name
        
        # effective_config 로드
        config_file = run_dir / "effective_config.yml"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                cfg = yaml.safe_load(f)
            
            paper_cfg = cfg.get('paper', {})
            start_time = paper_cfg.get('start_time', 'N/A')
            duration_hours = paper_cfg.get('duration_hours', 'N/A')
            
            logger.info(f"\n[{i}] Run ID: {run_id}")
            logger.info(f"    시작: {start_time}")
            logger.info(f"    Duration: {duration_hours} hours")
            
            # Scorecard 확인
            scorecard_file = run_dir / "scorecard.csv"
            if scorecard_file.exists():
                logger.info(f"    ✅ Scorecard 생성됨")
                
                # CSV 읽기
                try:
                    import pandas as pd
                    df = pd.read_csv(scorecard_file)
                    
                    # 주요 지표 출력
                    metrics = {}
                    for _, row in df.iterrows():
                        metrics[row['Metric']] = row['Value']
                    
                    logger.info(f"    📊 Trades: {metrics.get('Trades Closed', 0)}")
                    logger.info(f"    📊 Winrate: {metrics.get('Winrate (%)', 0)}%")
                    logger.info(f"    📊 PF: {metrics.get('Profit Factor', 0)}")
                    logger.info(f"    📊 Max DD: {metrics.get('Max Drawdown (%)', 0)}%")
                except Exception as e:
                    logger.warning(f"    ⚠️ Scorecard 파싱 실패: {e}")
            else:
                logger.warning(f"    ⚠️ Scorecard 없음")
        else:
            logger.info(f"\n[{i}] Run ID: {run_id} (config 없음)")
    
    logger.info("\n" + "=" * 70)


def main():
    """메인 함수"""
    logger.info("=" * 70)
    logger.info("🔍 PHASE16 Paper Trading Status Check")
    logger.info("=" * 70)
    
    # 1. Redis 상태 확인
    logger.info("\n[1] Redis 상태 확인")
    check_redis()
    
    # 2. 최근 runs 확인
    logger.info("\n[2] 최근 Paper Trading Runs")
    check_recent_runs()
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ 상태 확인 완료")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
