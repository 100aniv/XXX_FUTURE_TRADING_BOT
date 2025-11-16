#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE16 Paper Trading Monitor
==============================
실시간 Paper trading 모니터링

Usage:
    python scripts/monitor_paper.py
"""
import sys
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


def monitor_loop(interval=10):
    """모니터링 루프 (텍스트 모드)"""
    
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
        
        redis_available = True
        client.ping()
    except Exception as e:
        logger.error(f"❌ Redis 연결 실패: {e}")
        redis_available = False
    
    logger.info("=" * 80)
    logger.info("🔄 PHASE16 Paper Trading Monitor - {interval}초 주기 갱신")
    logger.info("   Ctrl+C로 종료")
    logger.info("=" * 80)
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            print("\n" + "=" * 80)
            print(f"⏰ {current_time} | 갱신 #{iteration}")
            print("=" * 80)
            
            # Redis 상태
            if redis_available:
                try:
                    dedup_keys = len(client.keys("dedup:*"))
                    cooldown_keys = len(client.keys("cooldown:*"))
                    signal_keys = len(client.keys("signal:*"))
                    
                    print(f"\n📊 Redis 키 현황:")
                    print(f"   Dedup: {dedup_keys}개")
                    print(f"   Cooldown: {cooldown_keys}개")
                    print(f"   Signal: {signal_keys}개")
                except Exception as e:
                    print(f"   ⚠️ Redis 조회 실패: {e}")
            else:
                print("\n⚠️ Redis 연결 없음")
            
            # 최근 run 확인
            scorecard_dir = Path("scorecards/paper_phase16")
            if scorecard_dir.exists():
                runs = sorted([d for d in scorecard_dir.iterdir() if d.is_dir()], reverse=True)
                
                if runs:
                    latest_run = runs[0]
                    print(f"\n📁 최신 Run: {latest_run.name}")
                    
                    # Scorecard 확인
                    scorecard_file = latest_run / "scorecard.csv"
                    if scorecard_file.exists():
                        try:
                            import pandas as pd
                            df = pd.read_csv(scorecard_file)
                            
                            metrics = {}
                            for _, row in df.iterrows():
                                metrics[row['Metric']] = row['Value']
                            
                            print(f"   Trades: {metrics.get('Trades Closed', 0)}")
                            print(f"   Winrate: {metrics.get('Winrate (%)', 0)}%")
                            print(f"   PF: {metrics.get('Profit Factor', 0)}")
                        except Exception as e:
                            print(f"   ⚠️ Scorecard 파싱 실패: {e}")
                    else:
                        print(f"   ⏳ Scorecard 생성 대기 중...")
                else:
                    print("\n⚠️ Paper trading run이 없습니다")
            
            print("\n" + "=" * 80)
            print(f"⏳ {interval}초 후 갱신... (Ctrl+C로 종료)")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  모니터링 종료")
        sys.exit(0)


def main():
    """메인 함수"""
    monitor_loop(interval=10)


if __name__ == "__main__":
    main()
