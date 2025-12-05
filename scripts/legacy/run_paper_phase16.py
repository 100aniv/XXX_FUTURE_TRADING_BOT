#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE16: 12-Hour Paper Trading Pipeline
========================================

목표:
- PHASE15 Best 파라미터로 12시간 Paper Trading 실행
- Redis 기반 실시간 모니터링
- 자동 이벤트 기록 및 스냅샷

사용법:
    python scripts/run_paper_phase16.py
"""
from __future__ import annotations
import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import redis
import yaml
import pandas as pd
from common.config_loader import load_config_with_mode
from common.logger import setup_logger as setup_app_logger
from analytics.scorecard import ScorecardGenerator


# =====================================================================
# Configuration
# =====================================================================

PHASE16_CONFIG = {
    "mode": "paper",
    "duration_hours": 12,
    "redis_namespace": "paper:phase16",
    "snapshot_interval_minutes": 60,
    "log_dir": "logs/paper_phase16",
    "scorecard_dir": "scorecards/paper_phase16",
}

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))


# =====================================================================
# Logging Setup
# =====================================================================

def setup_logging(log_dir: Path) -> tuple[logging.Logger, Path]:
    """로깅 설정"""
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / timestamp / "application.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("PHASE16")
    logger.setLevel(logging.DEBUG)
    
    # File handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger, log_file.parent


# =====================================================================
# Redis Helpers
# =====================================================================

class RedisTracker:
    """Redis 기반 상태 추적"""
    
    def __init__(self, namespace: str):
        self.r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
        self.namespace = namespace
        self.start_time = datetime.now()
    
    def set_state(self, state: str, details: Optional[Dict] = None):
        """엔진 상태 저장"""
        key = f"{self.namespace}:state"
        value = {
            "state": state,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.r.set(key, json.dumps(value))
    
    def add_position(self, symbol: str, side: str, entry: float, tp: float, sl: float):
        """포지션 추가"""
        key = f"{self.namespace}:positions"
        position = {
            "symbol": symbol,
            "side": side,
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "timestamp": datetime.now().isoformat()
        }
        self.r.lpush(key, json.dumps(position))
    
    def add_metric(self, metric_name: str, value: float):
        """메트릭 추가"""
        key = f"{self.namespace}:metrics"
        metric = {
            "name": metric_name,
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        self.r.lpush(key, json.dumps(metric))
    
    def add_error(self, error_msg: str):
        """에러 로그"""
        key = f"{self.namespace}:errors"
        error = {
            "message": error_msg,
            "timestamp": datetime.now().isoformat()
        }
        self.r.lpush(key, json.dumps(error))
    
    def get_state(self) -> Dict:
        """현재 상태 조회"""
        key = f"{self.namespace}:state"
        data = self.r.get(key)
        return json.loads(data) if data else {}
    
    def get_positions(self, limit: int = 10) -> list:
        """최근 포지션 조회"""
        key = f"{self.namespace}:positions"
        positions = self.r.lrange(key, 0, limit - 1)
        return [json.loads(p) for p in positions]
    
    def get_metrics(self, limit: int = 100) -> list:
        """메트릭 조회"""
        key = f"{self.namespace}:metrics"
        metrics = self.r.lrange(key, 0, limit - 1)
        return [json.loads(m) for m in metrics]
    
    def get_errors(self, limit: int = 50) -> list:
        """에러 로그 조회"""
        key = f"{self.namespace}:errors"
        errors = self.r.lrange(key, 0, limit - 1)
        return [json.loads(e) for e in errors]


# =====================================================================
# Paper Trading Engine
# =====================================================================

class PaperTradingPhase16:
    """PHASE16 Paper Trading Pipeline"""
    
    def __init__(self, logger: logging.Logger, log_dir: Path):
        self.logger = logger
        self.log_dir = log_dir
        self.tracker = RedisTracker(PHASE16_CONFIG["redis_namespace"])
        
        # Load PHASE15 Best parameters
        self.config = self._load_phase15_config()
        
        # Initialize engine (will be set up in initialize())
        self.engine = None
        self.portfolio = None
        self.run_id = None
        self.output_dir = None
        
        # Metrics
        self.start_time = datetime.now()
        self.trades_count = 0
        self.wins = 0
        self.losses = 0
        self.max_dd = 0.0
        self.pnl = 0.0
    
    def _load_phase15_config(self) -> Dict:
        """PHASE15 Best 파라미터 로드"""
        config_path = Path("configs/scalping/active.yml")
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found: {config_path}")
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        self.logger.info(f"✅ PHASE15 Best 파라미터 로드 완료")
        self.logger.info(f"   rr={config['scalping']['rr']}, "
                        f"atr_mult_sl={config['scalping']['atr_mult_sl']}, "
                        f"max_hold_minutes={config['scalping']['max_hold_minutes']}")
        
        return config
    
    def initialize(self):
        """초기화"""
        self.logger.info("=" * 70)
        self.logger.info("🚀 PHASE16 Paper Trading 초기화 중...")
        self.logger.info("=" * 70)
        
        try:
            # Redis 상태 초기화
            self.tracker.set_state("INITIALIZING", {
                "start_time": self.start_time.isoformat(),
                "duration_hours": PHASE16_CONFIG["duration_hours"]
            })
            
            # Run ID 생성
            self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_phase16"
            
            # Output directory 생성
            scorecard_base = Path(PHASE16_CONFIG["scorecard_dir"])
            self.output_dir = scorecard_base / self.run_id
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"📁 Output Directory: {self.output_dir}")
            self.logger.info(f"📊 Run ID: {self.run_id}")
            
            # TODO: Engine 초기화는 실제 Paper 모드 실행 시 구현 필요
            # 현재는 스켈레톤 모드로 메트릭만 시뮬레이션
            self.logger.info("⚠️  WARNING: Paper Trading은 현재 시뮬레이션 모드입니다")
            self.logger.info("⚠️  실제 Engine 통합은 향후 구현 예정")
            
            self.logger.info("✅ 초기화 완료")
            self.tracker.set_state("READY")
            
        except Exception as e:
            self.logger.error(f"❌ 초기화 실패: {e}", exc_info=True)
            self.tracker.add_error(str(e))
            raise
    
    def run(self):
        """12시간 Paper Trading 실행"""
        self.logger.info("=" * 70)
        self.logger.info("🟢 PHASE16 Paper Trading 시작")
        self.logger.info("=" * 70)
        
        self.tracker.set_state("RUNNING")
        
        end_time = self.start_time + timedelta(hours=PHASE16_CONFIG["duration_hours"])
        last_snapshot = self.start_time
        
        try:
            while datetime.now() < end_time:
                # Periodic snapshot
                if (datetime.now() - last_snapshot).total_seconds() >= \
                   PHASE16_CONFIG["snapshot_interval_minutes"] * 60:
                    self._save_snapshot()
                    last_snapshot = datetime.now()
                
                # TODO: 실제 Paper Trading 루프 구현
                # 현재는 시뮬레이션 모드로 메트릭만 업데이트
                # In real implementation, this would:
                # 1. Fetch market data
                # 2. Generate signals
                # 3. Place dry-run orders
                # 4. Track positions
                # 5. Update metrics
                
                # 시뮬레이션: 랜덤 메트릭 업데이트 (실제 구현 시 제거)
                import random
                if random.random() < 0.01:  # 1% 확률로 거래 발생
                    self.trades_count += 1
                    if random.random() < 0.3:  # 30% 승률
                        self.wins += 1
                        self.pnl += random.uniform(0.5, 2.0)
                    else:
                        self.losses += 1
                        self.pnl -= random.uniform(0.3, 1.0)
                    
                    # Redis에 메트릭 기록
                    self.tracker.add_metric("trades", self.trades_count)
                    self.tracker.add_metric("pnl", self.pnl)
                
                time.sleep(10)  # Check every 10 seconds
                
                # Log progress
                elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
                if int(elapsed * 60) % 10 == 0:  # 10분마다 로그
                    self.logger.info(f"⏱️  경과 시간: {elapsed:.2f}h / {PHASE16_CONFIG['duration_hours']}h | "
                                   f"거래: {self.trades_count}건 | PnL: {self.pnl:.2f}")
        
        except KeyboardInterrupt:
            self.logger.info("⏹️  사용자 중단 신호 수신")
        except Exception as e:
            self.logger.error(f"❌ 실행 중 오류: {e}")
            self.tracker.add_error(str(e))
        finally:
            self.finalize()
    
    def _save_snapshot(self):
        """스냅샷 저장"""
        self.logger.info("💾 스냅샷 저장 중...")
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
            "trades": self.trades_count,
            "wins": self.wins,
            "losses": self.losses,
            "max_dd": self.max_dd,
        }
        
        snapshot_file = self.log_dir / "snapshots.jsonl"
        with open(snapshot_file, "a") as f:
            f.write(json.dumps(snapshot) + "\n")
        
        self.logger.info(f"✅ 스냅샷 저장 완료: {snapshot}")
    
    def finalize(self):
        """종료 및 리포트 생성"""
        self.logger.info("=" * 70)
        self.logger.info("⏹️  PHASE16 Paper Trading 종료")
        self.logger.info("=" * 70)
        
        # 최종 메트릭 계산
        winrate = (self.wins / self.trades_count * 100) if self.trades_count > 0 else 0
        
        self.tracker.set_state("FINISHED", {
            "end_time": datetime.now().isoformat(),
            "total_trades": self.trades_count,
            "wins": self.wins,
            "losses": self.losses,
            "winrate": winrate,
            "pnl": self.pnl,
            "max_dd": self.max_dd
        })
        
        # Generate scorecard
        self._generate_scorecard()
        
        # Generate report
        self._generate_report()
        
        self.logger.info("✅ PHASE16 완료")
        self.logger.info(f"📊 최종 결과: 거래 {self.trades_count}건 | 승률 {winrate:.1f}% | PnL {self.pnl:.2f}")
    
    def _generate_scorecard(self):
        """Scorecard CSV 생성"""
        self.logger.info("📊 Scorecard 생성 중...")
        
        try:
            winrate = (self.wins / self.trades_count * 100) if self.trades_count > 0 else 0
            profit_factor = 0.0  # TODO: 실제 계산
            
            scorecard_data = {
                "Metric": [
                    "Strategy",
                    "Symbol",
                    "Timeframe",
                    "Trades Closed",
                    "Winrate (%)",
                    "Profit Factor",
                    "Max Drawdown (%)",
                    "PnL",
                    "TP Hit (%)",
                    "Sharpe Ratio"
                ],
                "Value": [
                    "scalping",
                    "BTCUSDT",
                    "3m",
                    self.trades_count,
                    f"{winrate:.2f}",
                    f"{profit_factor:.2f}",
                    f"{self.max_dd:.2f}",
                    f"{self.pnl:.2f}",
                    "0.0",
                    "0.0"
                ]
            }
            
            df = pd.DataFrame(scorecard_data)
            scorecard_file = self.output_dir / "scorecard.csv"
            df.to_csv(scorecard_file, index=False)
            
            self.logger.info(f"✅ Scorecard 저장: {scorecard_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Scorecard 생성 실패: {e}", exc_info=True)
    
    def _generate_report(self):
        """리포트 생성"""
        self.logger.info("📝 리포트 생성 중...")
        
        elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
        winrate = (self.wins / self.trades_count * 100) if self.trades_count > 0 else 0
        
        report = f"""
# PHASE16 Paper Trading Report

## 실행 결과

- **시작 시간**: {self.start_time.isoformat()}
- **종료 시간**: {datetime.now().isoformat()}
- **경과 시간**: {elapsed:.2f}h / {PHASE16_CONFIG['duration_hours']}h

## 성능 지표

- **총 거래**: {self.trades_count}
- **승리**: {self.wins}
- **패배**: {self.losses}
- **승률**: {winrate:.1f}%
- **최대 낙폭**: {self.max_dd:.2f}%

## PHASE15 Best 파라미터

```yaml
{yaml.dump(self.config['scalping'], default_flow_style=False)}
```

## 결론

Paper Trading 테스트 완료. 결과를 분석하여 PHASE17 진행 여부 결정.
"""
        
        report_file = Path(PHASE16_CONFIG["scorecard_dir"]) / \
                     datetime.now().strftime("%Y%m%d_%H%M%S") / \
                     "PHASE16_PAPER_REPORT.md"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, "w") as f:
            f.write(report)
        
        self.logger.info(f"✅ 리포트 저장: {report_file}")


# =====================================================================
# Main
# =====================================================================

def main():
    """메인 함수"""
    
    # Logging setup
    log_dir = Path(PHASE16_CONFIG["log_dir"])
    logger, log_path = setup_logging(log_dir)
    
    logger.info("=" * 70)
    logger.info("🚀 PHASE16 Paper Trading Pipeline")
    logger.info("=" * 70)
    logger.info(f"📍 Log Directory: {log_path}")
    logger.info(f"📍 Redis Namespace: {PHASE16_CONFIG['redis_namespace']}")
    logger.info(f"⏱️  Duration: {PHASE16_CONFIG['duration_hours']} hours")
    logger.info("=" * 70)
    
    try:
        # Initialize and run
        paper_trading = PaperTradingPhase16(logger, log_path)
        paper_trading.initialize()
        paper_trading.run()
        
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
