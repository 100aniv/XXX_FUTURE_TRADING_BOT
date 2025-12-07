#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PHASE28-5: Local Grid Search Round 1 - Sequential Execution
============================================================
Bayesian Round 1 상위 trials 주변에서 국지 Grid Search 실행

주요 기능:
1. 환경 검증 (Python version, DB)
2. PHASE28-4 Bayesian Round 1 결과에서 Top-K seeds 추출
3. Local Grid Search 순차 실행 (seed별)
4. 결과 집계 및 리포트 생성

Usage:
    python scripts/tuning/phase28_5_run_local_grid_search_round1.py
    python scripts/tuning/phase28_5_run_local_grid_search_round1.py --config configs/tuning/phase28_5_btc5m_local_grid_search.yml
"""
import sys
import os
import argparse
import time
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from database import get_db_connection
from tuning.algorithms.random_search import ParamSpace
from tuning.algorithms.local_grid_search import LocalGridSearchTuner
from common.logger import setup_logger

logger = setup_logger(__name__, log_type="application")


# ========================================
# Environment Check
# ========================================

def check_environment() -> bool:
    """환경 검증: Python version, DB"""
    logger.info("=" * 80)
    logger.info("🔍 Environment Check")
    logger.info("=" * 80)
    
    # Python version
    if sys.version_info < (3, 9):
        logger.error(f"❌ Python 3.9+ required (current: {sys.version})")
        return False
    logger.info(f"✅ Python version: {sys.version.split()[0]}")
    
    # Postgres
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                logger.info(f"✅ Postgres reachable: {version.split(',')[0]}")
    except Exception as e:
        logger.error(f"❌ Postgres unreachable: {e}")
        return False
    
    logger.info("=" * 80)
    return True


# ========================================
# Load Configuration
# ========================================

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML"""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"✅ Config loaded: {config_path}")
    return config


def load_param_space(param_space_path: str) -> ParamSpace:
    """Load ParamSpace from YAML"""
    ps_file = Path(param_space_path)
    if not ps_file.exists():
        raise FileNotFoundError(f"ParamSpace YAML not found: {param_space_path}")
    
    with open(ps_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    param_space_dict = data.get('param_space', {})
    param_space = ParamSpace(space=param_space_dict)
    param_space.validate()
    
    logger.info(f"✅ ParamSpace loaded: {len(param_space_dict)} params")
    return param_space


# ========================================
# Seed Selection from PHASE28-4
# ========================================

def select_seed_trials(
    run_id_prefix: str,
    top_k: int,
    min_trades: int,
    target_metric: str = 'sharpe_ratio'
) -> List[Dict[str, Any]]:
    """
    PHASE28-4 Bayesian Round 1 결과에서 Top-K seed trials 선택
    
    Args:
        run_id_prefix: Run ID prefix (예: 'phase28_4_')
        top_k: 상위 K개
        min_trades: 최소 거래 수 (필터링)
        target_metric: 목표 메트릭
    
    Returns:
        Seed trial 리스트 [{'params_json': {...}, 'metrics': {...}}, ...]
    """
    logger.info("=" * 80)
    logger.info(f"🌱 Selecting Seed Trials from PHASE28-4")
    logger.info("=" * 80)
    logger.info(f"Source Run ID Prefix: {run_id_prefix}")
    logger.info(f"Top K: {top_k}")
    logger.info(f"Min Trades: {min_trades}")
    logger.info(f"Target Metric: {target_metric}")
    
    # DB에서 PHASE28-4 결과 조회
    sql = """
    SELECT
        j.job_id,
        j.params_json,
        r.trade_count,
        r.sharpe_ratio,
        r.pnl,
        r.win_rate,
        r.metrics_json
    FROM tuning.jobs j
    JOIN tuning.results r ON j.job_id = r.job_id
    WHERE j.run_id LIKE %s
      AND j.status = 'COMPLETED'
      AND r.trade_count >= %s
    ORDER BY r.sharpe_ratio DESC
    LIMIT %s
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (f"{run_id_prefix}%", min_trades, top_k))
            rows = cur.fetchall()
    
    if not rows:
        logger.warning(f"⚠️  No valid trials found in PHASE28-4 (run_id LIKE '{run_id_prefix}%', trades >= {min_trades})")
        return []
    
    seed_trials = []
    for idx, row in enumerate(rows, 1):
        job_id = row[0]
        params_json = row[1]
        trade_count = row[2]
        sharpe = row[3]
        pnl = row[4]
        win_rate = row[5]
        metrics_json = row[6]
        
        logger.info(f"  Seed {idx}: job_id={job_id[:12]}...")
        logger.info(f"    Sharpe={sharpe:.4f}, PnL={pnl:.2f}, Trades={trade_count}, Win%={win_rate:.2%}")
        logger.info(f"    Params: {params_json}")
        
        seed_trials.append({
            'job_id': job_id,
            'params_json': params_json,
            'metrics': metrics_json
        })
    
    logger.info("=" * 80)
    logger.info(f"✅ Selected {len(seed_trials)} seed trials")
    logger.info("=" * 80)
    
    return seed_trials


# ========================================
# Main Execution
# ========================================

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="PHASE28-5: Local Grid Search Round 1"
    )
    parser.add_argument(
        '--config',
        type=str,
        default='configs/tuning/phase28_5_btc5m_local_grid_search.yml',
        help='Config YAML path'
    )
    
    args = parser.parse_args()
    
    # 환경 검증
    if not check_environment():
        logger.error("❌ Environment check failed")
        sys.exit(1)
    
    # Config 로드
    config = load_config(args.config)
    
    # ParamSpace 로드
    param_space_path = config.get('param_space_path')
    param_space = load_param_space(param_space_path)
    
    # Seed trials 선택
    source_config = config.get('source', {})
    seed_trials = select_seed_trials(
        run_id_prefix=source_config.get('run_id_prefix', 'phase28_4_'),
        top_k=source_config.get('top_k_trials', 3),
        min_trades=source_config.get('min_trades', 5),
        target_metric=config.get('target_metric', 'sharpe_ratio')
    )
    
    if not seed_trials:
        logger.error("❌ No seed trials found, aborting")
        sys.exit(1)
    
    # Local Grid Search 실행
    logger.info("\n")
    logger.info("=" * 80)
    logger.info("🚀 Starting Local Grid Search Round 1")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    tuner = LocalGridSearchTuner()
    run_ids = tuner.run_from_seeds(
        run_id_prefix=config.get('base_run_id_prefix', 'phase28_5_localgrid'),
        seed_trials=seed_trials,
        param_space=param_space,
        grid_config=config.get('grid_config', {}),
        base_config_path=config.get('base_config_path'),
        mode=config.get('mode', 'backtest'),
        strategy_name=config.get('strategy', {}).get('name', 'btc5m_baseline_v1'),
        target_metric=config.get('target_metric', 'sharpe_ratio')
    )
    
    elapsed_time = time.time() - start_time
    
    logger.info("=" * 80)
    logger.info(f"🎉 Local Grid Search Round 1 Completed")
    logger.info("=" * 80)
    logger.info(f"Execution Time: {elapsed_time:.2f}s ({elapsed_time/60:.2f}m)")
    logger.info(f"Generated Runs: {len(run_ids)}")
    for idx, run_id in enumerate(run_ids, 1):
        logger.info(f"  Run {idx}: {run_id}")
    logger.info("=" * 80)
    
    # 다음 단계 안내
    logger.info("\n📋 Next Steps:")
    logger.info("  1. Check progress:")
    logger.info("     python scripts/temp_check_phase28_5_progress.py")
    logger.info("  2. Summarize results:")
    logger.info("     python scripts/tuning/phase28_5_summarize_local_grid_round1.py")
    logger.info("=" * 80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
